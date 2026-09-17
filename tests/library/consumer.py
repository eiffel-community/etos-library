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
"""Messagebus consumer for ETOS internal messaging for tests to use."""

import asyncio
import json
import threading

from rstream import AMQPMessage, Consumer, MessageContext, amqp_decoder

from etos_lib.messaging.events import parse

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments


class SimpleConsumer(threading.Thread):
    """A simple consumer that runs in a separate thread and consumes messages from RabbitMQ."""

    def __init__(
        self,
        host,
        stream_name,
        username=None,
        password=None,
        port=5552,
        vhost=None,
    ):
        """Set up parameters for a rabbitmq stream connection."""
        super().__init__()
        self.__parameters = {
            "host": host,
            "port": port,
            "vhost": vhost,
            "username": username,
            "password": password,
        }
        self.stream_name = stream_name
        self.__received_messages = []
        self.__shutdown = asyncio.Event()
        self.__closed = threading.Event()
        self.__started = threading.Event()
        self.__lock = threading.Lock()

    async def __receive(self, msg: AMQPMessage, _: MessageContext) -> None:
        """Call back for consuming messages."""
        event = parse(json.loads(msg.body))
        with self.__lock:
            self.__received_messages.append(event.model_dump())

    async def __consume_forever(self, consumer: Consumer):
        """Consume messages indefinitely until shutdown signal is received."""
        await consumer.subscribe(
            stream=self.stream_name,
            callback=self.__receive,
            decoder=amqp_decoder,
        )
        if not self.__started.is_set():
            self.__started.set()
        await self.__shutdown.wait()  # Wait until shutdown signal is set

    async def __wrap_consumer(self):
        """Wrap the consumer in an async context manager to ensure proper cleanup."""
        async with Consumer(**self.__parameters) as consumer:
            await consumer.create_stream(self.stream_name, exists_ok=True)
            try:
                await self.__consume_forever(consumer)
            finally:
                await consumer.delete_stream(self.stream_name, missing_ok=True)
                await consumer.close()

    def run(self):
        """Run the consumer, consuming messages from the stream until shutdown."""
        try:
            asyncio.run(self.__wrap_consumer())
        finally:
            self.__closed.set()

    @property
    def received_messages(self):
        """Return the list of received messages."""
        with self.__lock:
            return self.__received_messages

    def wait_start(self, timeout: float = 60.0):
        """Wait for the consumer to start, meaning it has started consuming messages."""
        if not self.__started.wait(timeout=timeout):
            raise TimeoutError("Timeout while waiting for consumer to start")

    def wait_closed(self, timeout: float = 60.0):
        """Wait for the consumer to close, meaning it has stopped consuming messages."""
        if not self.__closed.wait(timeout=timeout):
            raise TimeoutError("Timeout while waiting for consumer to close")

    def close(self):
        """Close the consumer, signaling it to stop consuming messages."""
        self.__shutdown.set()
