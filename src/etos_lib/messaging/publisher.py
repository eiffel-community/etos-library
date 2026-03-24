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
"""ETOS messaging event publisher."""

import asyncio
import logging
import ssl as _ssl
import threading
import time

from rstream import AMQPMessage, ConfirmationStatus, Producer

from .events import Event

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-instance-attributes


class Publisher(threading.Thread):
    """Publisher that runs in a separate thread and publishes messages to RabbitMQ."""

    logger = logging.getLogger(__name__)

    __confirmed: int = 0
    __unconfirmed: int = 0
    __parent_thread: threading.Thread
    __loop: None | asyncio.AbstractEventLoop = None

    def __init__(
        self,
        host,
        stream_name,
        username=None,
        password=None,
        port=5552,
        vhost=None,
        ssl=True,
    ):
        """Set up parameters for a rabbitmq stream connection."""
        super().__init__()
        self.__shutdown = threading.Event()
        self.__closed = threading.Event()
        self.__started = threading.Event()
        self.__lock = threading.Lock()
        self.__queue = asyncio.Queue()
        self.__parameters = {
            "host": host,
            "port": port,
            "vhost": vhost,
            "username": username,
            "password": password,
        }
        if ssl is True:
            self.__parameters["ssl_context"] = _ssl.create_default_context()
        self.stream_name = stream_name
        self.__parent_thread = threading.current_thread()

    def run(self):
        """Run the publisher, consuming messages from the queue and publishing them."""
        # Register the close method to be called when the thread is exiting, ensuring that
        # resources are cleaned up properly.
        # Since this is not a daemon thread the regular atexit handlers won't be called when the
        # main thread shuts down, so we need to use the protected _register_atexit method to
        # ensure that the close method is called when the main thread is exiting.

        # Our reason for not running this as a daemon thread is that if the interpreter exits
        # (which is what triggers atexit) it will shutdown the threadpoolexecutor used in asyncio,
        # which will cause the cleanup to crash with a RuntimeError.
        threading._register_atexit(self.close, wait=True)  # pylint:disable=protected-access
        try:
            asyncio.run(self.__wrap_producer())
        finally:
            self.__closed.set()
        self.logger.debug("Publisher thread exiting")

    def close(self, wait: bool = False):
        """Close the publisher, signaling it to stop consuming messages."""
        self.logger.debug("Stopping thread")
        self.__shutdown.set()
        if wait:
            self.wait_closed(timeout=60)

    def is_alive(self) -> bool:
        """Check if the publisher is alive, meaning it has not shutdown or closed."""
        return (
            self.__started.is_set() and not self.__closed.is_set() and not self.__shutdown.is_set()
        )

    def wait_start(self, timeout: float = 60.0):
        """Wait for the publisher to start, meaning it has started consuming messages."""
        if not self.__started.wait(timeout=timeout):
            raise TimeoutError("Timeout while waiting for publisher to start")

    def wait_closed(self, timeout: float = 60.0):
        """Wait for the publisher to close, meaning it has stopped consuming messages."""
        if not self.__closed.wait(timeout=timeout):
            raise TimeoutError("Timeout while waiting for publisher to close")

    async def __consume_forever(self, producer: Producer):
        """Consume messages from the queue and publish them until shutdown is requested."""
        self.logger.debug("Consuming forever")
        while True:
            await asyncio.sleep(0.1)
            if not self.__started.is_set():
                self.__loop = asyncio.get_running_loop()
                self.logger.debug("Publisher started")
                self.__started.set()
            # Main thread died, shut down.
            if not self.__parent_thread.is_alive() and not self.__shutdown.is_set():
                self.logger.debug("Main thread died, shutting down")
                self.close()
            await self.__consume_queue(producer)

            # If shutdown is requested and the queue is empty, wait for unpublished events and
            # break the loop.
            if self.__shutdown.is_set() and self.__queue.empty():
                self.logger.debug(
                    "Shutdown requested and queue is empty, waiting for unpublished events"
                )
                await self.__wait_for_unpublished_events(timeout=30)
                break
        self.__closed.set()
        self.logger.debug("Stopped consuming")

    async def __filter_value_extractor(self, message: AMQPMessage) -> str:
        """Extract the filter value from the message properties."""
        properties = message.application_properties
        if properties.get("meta", "") == "":
            properties["meta"] = "*"
        return f"{properties['identifier']}.{properties['type']}.{properties['meta']}"

    async def __wrap_producer(self):
        """Wrap the producer and consume messages until shutdown is requested."""
        async with Producer(
            **self.__parameters,
            filter_value_extractor=self.__filter_value_extractor,
        ) as producer:
            await self.__consume_forever(producer)

    async def __consume_queue(self, producer: Producer):
        """Consume messages from the queue and publish them until the queue is empty."""
        while not self.__queue.empty():
            message = await self.__queue.get()
            self.logger.debug("Publishing message: %r", message)
            await producer.send(
                self.stream_name,
                message,
                on_publish_confirm=self.__on_publish_confirm,
            )

    async def __on_publish_confirm(self, confirmation: ConfirmationStatus):
        """Publish confirm callback, increments a counter if the message was confirmed."""
        if confirmation.is_confirmed:
            self.logger.debug("Message confirmed: %r", confirmation)
            with self.__lock:
                self.__confirmed += 1

    async def __wait_for_unpublished_events(self, timeout: float):
        """Wait for unpublished events to be confirmed until the timeout is reached."""
        self.logger.debug("Waiting for unpublished events, timeout = %ds", timeout)
        timeout = time.time() + timeout
        while self.__unconfirmed > self.__confirmed:
            await asyncio.sleep(0.1)
            if time.time() > timeout:
                raise TimeoutError("Timeout while waiting for unpublished events")
        self.logger.debug("All events published")

    def publish(self, testrun_id: str, event: Event):
        """Send an event to the publisher, which will be published to RabbitMQ."""
        if not self.is_alive():
            raise RuntimeError("Publisher is not alive")
        if self.__loop is None:
            raise RuntimeError("Publisher loop is not running")
        amqp_message = AMQPMessage(
            body=bytes(event.model_dump_json(), encoding="utf-8"),
            application_properties={
                "identifier": testrun_id,
                "type": event.event.lower(),
                "meta": event.meta,
            },
        )
        # Since we are running the publisher in a separate thread, we need to use
        # run_coroutine_threadsafe to put the message in the queue.
        asyncio.run_coroutine_threadsafe(self.__queue.put(amqp_message), self.__loop)
        with self.__lock:
            self.__unconfirmed += 1
