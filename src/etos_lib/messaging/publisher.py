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
"""ETOS internal event publisher."""

import asyncio
import time
import logging
import ssl as _ssl
from typing import Optional
from threading import Thread, Event as ThreadEvent, main_thread

from rstream import Producer, AMQPMessage, ConfirmationStatus
from rstream.utils import MonotonicSeq

from .events import Event

# pylint:disable=too-many-instance-attributes
# pylint:disable=too-many-arguments,too-many-positional-arguments


class Publisher(Thread):
    """Internal messaging publisher for ETOS.

    This publisher is running in a thread because the library we are using
    is async only and we don't want asyncio to infect all of ETOS.
    The interface is non-async and can be called from any method.

    start() - Start up the publisher
    publish() - Publish an event
    stop() - Stop the publisher and wait for outstanding events.
             This is done automatically when the program shuts down.

    Example usage:

        # Make sure that the ETOS_RABBITMQ_* environment variables are set.
        from etos_lib.etos import ETOS as ETOS_LIBRARY
        from etos_lib.messaging.protocol import Shutdown, Result
        ETOS = ETOS_LIBRARY(...)
        PUBLISHER = ETOS.messagebus_publisher()
        PUBLISHER.publish("identifier", Shutdown(data=Result(
            conclusion="SUCCESSFUL",
            verdict="PASSED",
            description="Hello world",
        )))

    Example usage with logger:

        # Make sure that the ETOS_RABBITMQ_* environment variables are set.
        import logging
        from etos_lib.logging.logger import setup_logging, FORMAT_CONFIG
        setup_logging("name", "version", "environment", None)
        FORMAT_CONFIG.identifier = "identifier"
        LOGGEr = logging.getLogger(__name__)
        LOGGER.info("Hello world", extra={"user_log": True})
    """

    publisher_name = "etos_internal_messaging"
    context = None
    producer = None
    logger = logging.getLogger(__name__)

    def __init__(self, host, username=None, password=None, port=5671, vhost=None, ssl=True):
        """Initialize with host."""
        # self.logger.propagate = False
        super().__init__()
        if ssl is True:
            self.context = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        self.host = host
        self.username = username or ""
        self.password = password or ""
        self.port = port
        self.vhost = vhost or "/"
        self.started = ThreadEvent()
        self.stopped = ThreadEvent()
        self.__queue = asyncio.Queue()
        self.__sequences = {}
        self.__outstanding_deliveries = {}

    def publish(self, testrun_id: str, event: Event):
        """Publish an event to the internal messagebus."""
        self.logger.debug(
            "Publishing event '%s' to id %r",
            event,
            testrun_id,
            extra={"user_log": True},
        )
        if self.stopped.is_set():
            self.logger.debug("Publisher is stopped, won't publish event")
            return
        self.__queue.put_nowait((testrun_id, event))

    def run(self):
        """Start up the publisher."""
        if not self.started.is_set():
            Thread(target=self.__monitor).start()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.__run_publisher())

    def stop(self):
        """Stop sending new events."""
        self.stopped.set()

    def __monitor(self):
        """Monitor the publisher thread.

        This is a trick to force the publisher thread to stop when we close
        down the program.
        Since we don't want the publisher thread to either hang forever or
        close too early we create this monitor that waits for the main thread
        to close and then stops the publisher, causing the publisher to stop
        receiving new events, wait for unpublished events and then close down
        the connection.
        """
        thread = main_thread()
        thread.join()
        self.stop()

    async def __run_publisher(self):
        """Run the publisher until stop is called."""
        self.logger.debug("Publisher is starting up")
        await self.__start()
        try:
            while True:
                if self.stopped.is_set() and self.__queue.empty():
                    break
                try:
                    testrun_id, event = self.__queue.get_nowait()
                    await self.__setup_sequence(testrun_id)
                    await self.__publish(testrun_id, event)
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.01)
        finally:
            self.logger.debug("Publisher is closing down")
            await self.__wait_for_unpublished_events()
            await self.__close()
        self.logger.debug("Publisher has closed")

    async def __close(self):
        """Close the publisher."""
        if self.started.is_set():
            self.logger.debug("Closing down publisher")
            assert self.producer is not None
            try:
                await self.producer.close()
            except RuntimeError:
                pass
            self.__sequences = {}
            self.logger.debug("Successfully closed")

    async def __start(self):
        """Start up the publisher."""
        self.logger.debug("Starting up publisher")
        self.producer = Producer(
            host=self.host,
            vhost=self.vhost,
            username=self.username,
            password=self.password,
            port=self.port,
            ssl_context=self.context,
            filter_value_extractor=self.__filter_value_extractor,
        )
        await self.producer.start()
        self.started.set()
        self.logger.debug("Publisher successfully started")

    async def __setup_sequence(self, stream_id: str):
        """Set up sequence numbers for stream id in order to confirm deliveries.

        In order to confirm that all messages have been delivered we need to set
        the publishing ID on our messages, this publishing ID must be an ID that
        has not already been sent or the consumers won't accept the message.
        We get the client from the rstream library and get the current sequence
        number for the stream the same way that the rstream library does it.
        """
        if self.__sequences.get(stream_id) is None:
            assert self.producer is not None

            self.__sequences.setdefault(stream_id, MonotonicSeq())
            # pylint:disable=protected-access
            # This is a private method in the rstream library that we need to use
            # since it is the best way to get the sequence number for a stream.
            client = await self.producer._get_or_create_client(stream_id)
            sequence = await client.query_publisher_sequence(
                stream=stream_id,
                reference=self.publisher_name,
            )
            self.__sequences[stream_id].set(sequence + 1)

    async def __wait_for_unpublished_events(self, timeout=60):
        """Wait for all published events to be sent."""
        end = time.time() + timeout

        self.logger.debug("Waiting for unpublished events")
        deliveries = 0
        while time.time() < end:
            await asyncio.sleep(0.1)
            if len(self.__outstanding_deliveries) == 0:
                break
        else:
            raise TimeoutError(
                f"Timeout ({timeout:0.2f}s) while waiting for events to publish"
                f" ({deliveries} still unpublished)"
            )
        self.logger.debug("All unpublished events are sent")

    async def __filter_value_extractor(self, message: AMQPMessage) -> Optional[str]:
        """Create the filter that is sent with each AMQPMessage."""
        msg = None
        properties = message.application_properties
        if properties is not None:
            msg = f"{properties['identifier']}.{properties['type']}.{properties['meta']}"
        return msg

    async def __publish(self, stream_id: str, event: Event):
        """Asynchronous publish of event."""
        assert self.producer is not None

        publishing_id = self.__sequences[stream_id].next()
        self.logger.debug("Preparing to send '%s' with id '%d'", event, publishing_id)
        amqp_message = AMQPMessage(
            body=bytes(event.model_dump_json(), "utf-8"),
            application_properties={
                "identifier": stream_id,
                "type": event.event.lower(),
                "meta": event.meta,
            },
        )
        amqp_message.publishing_id = publishing_id

        self.logger.debug("AMQP message created, send it")
        await self.producer.send(
            publisher_name=self.publisher_name,
            stream=stream_id,
            message=amqp_message,
            on_publish_confirm=self._confirm_delivery,
        )
        self.__outstanding_deliveries[publishing_id] = (stream_id, event)
        self.logger.debug("AMQP message sent")

    async def _confirm_delivery(self, confirmation: ConfirmationStatus):
        """Confirm the delivery of events and make sure we resend NACKed events.

        Note: This only checks the broker, not from any consumer.
        """
        if confirmation.is_confirmed:
            self.__outstanding_deliveries.pop(confirmation.message_id)
        else:
            self.logger.warning(
                "Message (%d) was not acknowledged by the messaging server, requeueing it",
                confirmation.message_id,
            )
            self.__queue.put_nowait(self.__outstanding_deliveries.pop(confirmation.message_id))
