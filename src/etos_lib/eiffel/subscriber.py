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
"""Custom subscribers for eiffellib."""
import functools
import json
import logging
import traceback
from typing import Optional

import eiffellib.events
from eiffellib.events.eiffel_base_event import EiffelBaseEvent
from eiffellib.subscribers.rabbitmq_subscriber import RabbitMQSubscriber
from opentelemetry import context, propagate, trace
from opentelemetry.propagators.textmap import CarrierT, Getter
from opentelemetry.semconv.trace import MessagingOperationValues
from opentelemetry.trace import SpanKind
from pika.spec import Basic, BasicProperties

from .common import add_span_attributes, add_span_eiffel_attributes

_LOG = logging.getLogger(__name__)


class _Getter(Getter[CarrierT]):  # type: ignore
    """Getter for receiving a key from amqp headers."""

    def get(self, carrier: CarrierT, key: str) -> Optional[list[str]]:
        """Get a key from headers."""
        value = carrier.get(key, None)
        if value is None:
            return None
        return [value]

    def keys(self, carrier: CarrierT) -> list[str]:
        """Return an empy list of keys."""
        return []


_GETTER = _Getter()


class TracingRabbitMQSubscriber(RabbitMQSubscriber):
    """Custom RabbitMQ subscriber that gets otel trace information to headers."""

    def __init__(self, *args, **kwargs):
        """Get a trace."""
        # Must import this here, otherwise there would be a cyclic import problem.
        # pylint:disable=cyclic-import,import-outside-toplevel
        from etos_lib import __version__

        super().__init__(*args, **kwargs)
        self.tracer = trace.get_tracer(
            __name__,
            __version__,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )

    def _on_message(
        self, _, method: Basic.Deliver, properties: BasicProperties, body: bytes
    ) -> None:
        """On message callback. Called on each message. Will block if no place in queue.

        For each message attempt to acquire the `threading.Semaphore`. The semaphore
        size is `max_threads` + `max_queue`. This is to limit the amount of threads
        in the queue, waiting to be processed.
        For each message apply them async to a `ThreadPool` with size=`max_threads`.

        :param method: Pika basic deliver object.
        :param properties: Pika basic properties object.
        :param body: Message body.
        """
        self._RabbitMQSubscriber__workers.acquire()  # pylint:disable=no-member
        delivery_tag = method.delivery_tag
        error_callback = functools.partial(self.callback_error, delivery_tag)
        result_callback = functools.partial(self.callback_results, delivery_tag)
        self._RabbitMQSubscriber__thread_pool.apply_async(  # pylint:disable=no-member
            self._tracer_call,
            args=(body, method, properties),
            callback=result_callback,
            error_callback=error_callback,
        )

    def _tracer_call(
        self, body: bytes, method: Basic.Deliver, properties: BasicProperties
    ) -> tuple[bool, bool]:
        """Tracing callback for the custom subscriber that extracts a trace from amq headers."""
        if not properties:
            properties = BasicProperties(headers={})
        if properties.headers is None:
            properties.headers = {}
        ctx = propagate.extract(properties.headers, getter=_GETTER)
        if not ctx:
            ctx = context.get_current()
        token = context.attach(ctx)

        task_name = f"{method.exchange if method.exchange else self.routing_key} receive"
        span = self.tracer.start_span(
            name=task_name,
            kind=SpanKind.CONSUMER,
        )
        if span.is_recording():
            add_span_attributes(
                span,
                self._channel,
                properties,
                self.routing_key,
                MessagingOperationValues.RECEIVE,
                self.queue,
            )
        try:
            event = self._event(body)
        except:  # pylint:disable=bare-except
            # Pylint is wrong.. pylint:disable=not-context-manager
            with trace.use_span(span, end_on_exit=True) as span:
                raise
        if span.is_recording():
            add_span_eiffel_attributes(span, event)
        try:
            # Pylint is wrong.. pylint:disable=not-context-manager
            with trace.use_span(span, end_on_exit=True):
                response = self._event_call(event)
        finally:
            context.detach(token)
        return response

    def _event_call(self, event: EiffelBaseEvent) -> tuple[bool, bool]:
        """Call followers and subscribers of an event."""
        try:
            ack = self._call_subscribers(event.meta.type, event)
            self._call_followers(event)
        except:  # noqa, pylint:disable=bare-except
            _LOG.error(
                "Caught exception while processing subscriber "
                "callbacks, some callbacks may not have been called: %s",
                traceback.format_exc(),
            )
            ack = False
        return ack, True  # Requeue only if ack is False.

    def _event(self, body: bytes) -> EiffelBaseEvent:
        """Rebuild event."""
        # pylint:disable=broad-exception-raised
        try:
            json_data = json.loads(body.decode("utf-8"))
        except (json.decoder.JSONDecodeError, UnicodeDecodeError) as err:
            raise Exception(
                f"Unable to deserialize message body ({err}), rejecting: {body!r}"
            ) from err
        try:
            meta_type = json_data.get("meta", {}).get("type")
            event = getattr(eiffellib.events, meta_type)(json_data.get("meta", {}).get("version"))
        except (AttributeError, TypeError) as err:
            raise Exception(f"Malformed message. Rejecting: {json_data!r}") from err
        try:
            event.rebuild(json_data)
        except Exception as err:  # pylint:disable=broad-except
            raise Exception(f"Unable to deserialize message ({err}): {json_data!r}") from err
        return event
