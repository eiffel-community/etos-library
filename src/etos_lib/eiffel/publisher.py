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
"""Custom publishers for eiffellib."""
import logging
import time
from copy import deepcopy
from threading import current_thread

from eiffellib.events.eiffel_base_event import EiffelBaseEvent
from eiffellib.publishers.rabbitmq_publisher import RabbitMQPublisher
from opentelemetry import propagate, trace
from opentelemetry.semconv.trace import MessagingOperationValues
from opentelemetry.trace import SpanKind
from pika.spec import BasicProperties

from .common import add_event, add_span_attributes, add_span_eiffel_attributes

_LOG = logging.getLogger(__name__)


class TracingRabbitMQPublisher(RabbitMQPublisher):
    """Custom RabbitMQ publisher that propagates otel trace information to headers."""

    def __init__(self, *args, **kwargs):
        """Get a tracer."""
        # Must import this here, otherwise there would be a cyclic import problem.
        # pylint:disable=cyclic-import,import-outside-toplevel
        from etos_lib import __version__

        super().__init__(*args, **kwargs)
        self.tracer = trace.get_tracer(
            __name__,
            __version__,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )
        self.destination = f"{self.parameters.host},{self.parameters.virtual_host},{self.exchange}"

    def send_event(self, event: EiffelBaseEvent, block: bool = True) -> None:
        """Validate and send an eiffel event to the rabbitmq server.

        This method will set the source on all events if there is a source
        added to the :obj:`RabbitMQPublisher`.
        If the routing key is set to None in the :obj:`RabbitMQPublisher` this
        method will use the routing key from the event that is being sent.
        The event domainId will also be added to `meta.source` if it is set to
        anything other than the default value. If there is no domainId
        set on the event, then the domainId from the source in the
        :obj:`RabbitMQPublisher` will be used in the routing key, with a default
        value taken from the :obj:`eiffellib.events.eiffel_base_event.EiffelBaseEvent`.

        :param event: Event to send.
        :type event: :obj:`eiffellib.events.eiffel_base_event.EiffelBaseEvent`
        :param block: Set to True in order to block for channel to become ready.
                      Default: True
        :type block: bool
        """
        if block:
            self.wait_start()
            while self._channel is None or not self._channel.is_open:
                time.sleep(0.1)

        properties = BasicProperties(
            content_type="application/json", delivery_mode=2, headers={}, type=self.destination
        )

        source = deepcopy(self.source)
        if self.routing_key is None and event.domain_id != EiffelBaseEvent.domain_id:
            source = source or {}
            source["domainId"] = event.domain_id
        elif self.routing_key is None and source is not None:
            # EiffelBaseEvent.domain_id will be the default value.
            # By using that value instead of setting the default in this
            # method there will only be one place to set the default (the events).
            event.domain_id = source.get("domainId", EiffelBaseEvent.domain_id)
        if source is not None:
            event.meta.add("source", source)
        event.validate()
        routing_key = self.routing_key or event.routing_key

        task_name = f"{self.exchange if self.exchange else routing_key} send"
        span = self.tracer.start_span(
            name=task_name,
            kind=SpanKind.PRODUCER,
        )
        if span.is_recording():
            add_span_attributes(
                span,
                self._channel,
                properties,
                routing_key,
                MessagingOperationValues.PUBLISH,
            )
            add_span_eiffel_attributes(span, event)

        _LOG.debug("[%s] Attempting to acquire 'send_event' lock", current_thread().name)
        # Pylint is wrong.. pylint:disable=not-context-manager
        with self._lock, trace.use_span(span, end_on_exit=True) as _span:
            _LOG.debug("[%s] 'send_event' Lock acquired", current_thread().name)
            propagate.inject(properties.headers)
            if properties.headers == {}:  # Tracing is not enabled?
                properties.headers = None
            try:
                self._channel.basic_publish(
                    self.exchange,
                    routing_key,
                    event.serialized,
                    properties,
                )
                _span.add_event("Published event", attributes=add_event(event))
            except Exception as exception:  # pylint:disable=broad-except
                self._nacked_deliveries.append(event)
                _span.record_exception(exception, escaped=True)
                return
            self._delivered += 1
            self._deliveries[self._delivered] = event
        _LOG.debug("[%s] 'send_event' Lock released", current_thread().name)
