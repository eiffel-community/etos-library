# Copyright Axis Communications AB.
#
# For a full list of individual contributors, please see the commit history.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common functions for the eiffel helpers."""
from collections.abc import MutableMapping, Sequence
from typing import Iterable, Optional

from eiffellib.events.eiffel_base_event import EiffelBaseEvent
from opentelemetry.semconv.trace import MessagingOperationValues, SpanAttributes
from opentelemetry.trace.span import Span
from pika.channel import Channel
from pika.spec import BasicProperties

from ..lib.config import Config

PUBLISHER_TEMPLATE = "{SERVER_ADDRESS}:{SERVER_PORT},{RABBITMQ_VHOST},{RABBITMQ_EXCHANGE}"
CONSUMER_TEMPLATE = "{RABBITMQ_QUEUE_NAME}"
# pylint:disable=too-many-arguments,too-many-positional-arguments


def add_span_attributes(
    span: Span,
    channel: Channel,
    properties: BasicProperties,
    routing_key: str,
    operation: MessagingOperationValues,
    destination_name: Optional[str] = None,
) -> None:
    """Add rabbitmq properties to a span.

    Copied and modified from:
    https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-pika
    """
    ssl = bool(Config().get("rabbitmq").get("ssl"))

    span.set_attribute(SpanAttributes.MESSAGING_SYSTEM, "rabbitmq")
    span.set_attribute(SpanAttributes.MESSAGING_OPERATION, operation.value)
    span.set_attribute(SpanAttributes.MESSAGING_RABBITMQ_DESTINATION_ROUTING_KEY, routing_key)

    if destination_name is not None:
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_NAME, destination_name)
        span.set_attribute("messaging.destination_publish.name", properties.type)
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_TEMPLATE, CONSUMER_TEMPLATE)
    else:
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_NAME, properties.type)
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_TEMPLATE, PUBLISHER_TEMPLATE)

    span.set_attribute(SpanAttributes.NETWORK_PROTOCOL_NAME, "amqps" if ssl else "amqp")
    span.set_attribute(SpanAttributes.NETWORK_TYPE, "ipv4")
    span.set_attribute(SpanAttributes.NETWORK_TRANSPORT, "tcp")

    span.set_attribute(SpanAttributes.SERVER_ADDRESS, channel.connection.params.host)
    span.set_attribute(SpanAttributes.SERVER_PORT, channel.connection.params.port)


def add_span_eiffel_attributes(span: Span, event: EiffelBaseEvent) -> None:
    """Add Eiffel properties to a span."""
    span.set_attribute(SpanAttributes.EVENT_NAME, event.meta.type)
    span.set_attribute(SpanAttributes.MESSAGING_MESSAGE_ID, event.meta.event_id)


def _flatten(d: dict, parent_key: str = "", sep: str = ".") -> Iterable[tuple[str, str]]:
    """Flatten a dictionary to be compatible with opentelemetry."""
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from _flatten_dict(v, new_key, sep=sep).items()
        elif isinstance(v, list):
            for i, lv in enumerate(v):
                if isinstance(lv, str):
                    yield new_key, v
                    break
                if isinstance(lv, MutableMapping):
                    new_key = new_key + sep + str(i)
                    yield from _flatten_dict(lv, new_key, sep=sep).items()
        else:
            yield new_key, v


def _flatten_dict(d: MutableMapping, parent_key: str = "", sep: str = ".") -> dict:
    """Call flatten on a dictionary."""
    return dict(_flatten(d, parent_key, sep))


def _links_to_dict(links: Sequence) -> MutableMapping:
    """Convert an Eiffel links structure to a dictionary."""
    dict_links = {}
    for link in links:
        key = link["type"].lower()
        if key in dict_links:
            if not isinstance(dict_links[key], list):
                dict_links[key] = [dict_links[key]]
            dict_links[key].append(link["target"])
        else:
            dict_links[key] = link["target"]
    return dict_links


def add_event(event: EiffelBaseEvent) -> dict:
    """Add event data to a dictionary."""
    attributes = {}
    event_json = event.json
    event_json["links"] = _links_to_dict(event_json.pop("links"))
    attributes.update(**_flatten_dict(event_json, parent_key="eiffel"))
    return attributes
