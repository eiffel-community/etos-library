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
"""Tests for the messagebus publisher."""

import logging
import os
import time
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from etos_lib.messaging.events import Message
from etos_lib.messaging.publisher import Publisher
from etos_lib.messaging.types import Log
from tests.library.consumer import SimpleConsumer

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_STREAM_PORT = int(os.environ.get("RABBITMQ_STREAM_PORT", 5552))
RABBITMQ_USERNAME = os.environ.get("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", "/")
# pylint: disable=protected-access


class PublisherTests(unittest.TestCase):
    """Integration tests for the messagebus Publisher."""

    logger = logging.getLogger(__name__)

    def setUp(self):
        """Initialize the Publisher and a Consumer for each test."""
        self.published_messages = []  # To store expected messages

        parameters = {
            "host": RABBITMQ_HOST,
            "port": RABBITMQ_STREAM_PORT,
            "vhost": RABBITMQ_VHOST,
            "username": RABBITMQ_USERNAME,
            "password": RABBITMQ_PASSWORD,
        }
        # Use a unique stream name for each test to avoid conflicts and ensure isolation
        stream_name = str(uuid4())
        self.consumer = SimpleConsumer(**parameters, stream_name=stream_name)
        self.consumer.start()
        self.consumer.wait_start(timeout=10)
        self.publisher = Publisher(**parameters, stream_name=stream_name, ssl=False)
        self.publisher.start()
        self.publisher.wait_start(timeout=10)

        self.logger.info("Publisher and Consumer setup complete for test.")

    def tearDown(self):
        """Close the publisher and consumer after each test."""
        self.logger.info("TearDown: Closing publisher and consumer.")
        if self.publisher.is_publisher_alive():
            self.publisher.close(wait=True)
            self.publisher.join(timeout=5)
            if self.publisher.is_publisher_alive():
                self.fail("Publisher thread did not terminate in tearDown.")
        self.consumer.close()
        self.consumer.join(timeout=5)
        self.logger.info("TearDown complete.")

    def _create_sample_event(self, message_text="Test log message"):
        """Helper to create a sample event."""
        now = datetime.now(timezone.utc)
        log_data = Log(
            message=message_text,
            levelname="info",
            name="test_logger",
            datestring=now,
        )
        event = Message(id=time.time_ns(), data=log_data)
        self.published_messages.append(event.model_dump())
        return event

    def _wait_for_message_confirmation(
        self, publisher: Publisher, expected_count: int = 1, timeout: float = 5
    ) -> bool:
        """Helper to wait for a certain number of messages to be confirmed."""
        timeout = time.time() + timeout
        while time.time() < timeout:
            time.sleep(0.1)
            if publisher._Publisher__confirmed >= expected_count:
                break
        return publisher._Publisher__confirmed == expected_count

    def test_publisher_sends_and_consumer_receives(self):
        """Test that a message published by the Publisher is received by the Consumer."""
        self.assertTrue(self.publisher.is_publisher_alive())

        testrun_id = "test_run_123"
        event = self._create_sample_event("Hello RabbitMQ Stream!")

        self.logger.info("Publishing a message to the stream.")
        self.publisher.publish(testrun_id, event)
        self.logger.info("Published a message. Waiting for confirmation and receipt.")

        self.logger.info("Waiting for publisher to confirm the message.")
        self.assertTrue(
            self._wait_for_message_confirmation(self.publisher, expected_count=1, timeout=5)
        )

        self.logger.info("Waiting for consumer to receive the published message.")
        timeout = time.time() + 5
        while len(self.consumer.received_messages) < 1 and time.time() < timeout:
            time.sleep(0.1)

        self.logger.info("Verifying that the consumer received the published message.")
        self.assertEqual(
            len(self.consumer.received_messages),
            1,
            "Consumer did not receive the published message.",
        )
        self.assertDictEqual(self.consumer.received_messages[0], self.published_messages[0])

        self.logger.info("Successfully published and received one message.")

    def test_publisher_sends_multiple_messages_and_consumer_receives_all(self):
        """Test sending multiple messages and verifying all are received."""
        num_messages = 5
        testrun_id = "test_run_456"

        self.logger.info("Publishing %d messages to test multiple message handling.", num_messages)
        for i in range(num_messages):
            event = self._create_sample_event(f"Multi-message {i + 1}")
            self.publisher.publish(testrun_id, event)
        self.logger.info(
            "Published %d messages. Waiting for confirmation and receipt.", num_messages
        )

        self.logger.info("Waiting for publisher to confirm all messages.")
        self.assertTrue(
            self._wait_for_message_confirmation(
                self.publisher, expected_count=num_messages, timeout=10
            ),
            "Publisher did not confirm all messages within the timeout.",
        )

        # Wait for the consumer to actually receive all messages
        timeout = time.time() + 10
        while len(self.consumer.received_messages) < num_messages and (time.time() < timeout):
            time.sleep(0.1)

        self.logger.info("Verifying that the consumer received all published messages.")
        self.assertEqual(
            len(self.consumer.received_messages),
            num_messages,
            "Consumer did not receive all published messages.",
        )
        self.assertEqual(self.consumer.received_messages, self.published_messages)

        self.logger.info("Successfully published and received %d messages.", num_messages)

    def test_publisher_close_waits_for_unpublished_events(self):
        """
        Test that closing the publisher waits for all currently unconfirmed messages
        to be confirmed before shutting down.
        """
        testrun_id = "test_run_789"
        num_messages = 3

        self.logger.info(
            "Publishing %d messages and then closing the publisher to test waiting for "
            "unpublished events.",
            num_messages,
        )
        for i in range(num_messages):
            event = self._create_sample_event(f"Shutdown wait {i + 1}")
            self.publisher.publish(testrun_id, event)
            # Add a small delay to ensure messages are queued before attempting close
            time.sleep(0.01)

        self.logger.info(
            "Published %d messages. Initiating close and waiting for all to confirm.", num_messages
        )

        self.logger.info(
            "Verify that the publisher has the correct count of unconfirmed messages before close."
        )
        self.assertLessEqual(self.publisher._Publisher__confirmed, num_messages)
        self.assertEqual(self.publisher._Publisher__unconfirmed, num_messages)

        self.logger.info("Close the publisher to trigger waiting for unpublished events.")
        self.publisher.close(wait=True)
        self.publisher.wait_closed(timeout=10)  # Allow more time for network operations

        self.logger.info(
            "Verify that all messages were confirmed before the publisher fully closed."
        )
        self.assertFalse(
            self.publisher.is_publisher_alive(), "Publisher should not be alive after close."
        )
        self.assertEqual(
            self.publisher._Publisher__confirmed,
            num_messages,
            "Publisher did not confirm all messages before closing.",
        )
        self.assertEqual(
            self.publisher._Publisher__unconfirmed,
            num_messages,
            "Unconfirmed counter mismatch after close.",
        )

        self.logger.info(
            "Verify that the consumer received all messages published before shutdown."
        )
        timeout = time.time() + 5
        while len(self.consumer.received_messages) < num_messages and (time.time() < timeout):
            time.sleep(0.1)
        self.assertEqual(
            len(self.consumer.received_messages),
            num_messages,
            "Consumer did not receive all published messages during shutdown.",
        )
        self.assertEqual(self.consumer.received_messages, self.published_messages)

        self.logger.info(
            "Publisher successfully waited for all messages to confirm before closing."
        )

    def test_publish_when_publisher_not_alive(self):
        """Test that publish raises RuntimeError if publisher is not started."""
        self.logger.info("Stop the publisher to test publish behavior when not alive.")
        if self.publisher.is_publisher_alive():
            self.publisher.close(wait=True)
            self.publisher.join(timeout=5)

        event = self._create_sample_event()
        self.logger.info("Attempting to publish a message when the publisher is not alive.")
        with self.assertRaises(RuntimeError) as cm:
            self.publisher.publish("test_id", event)
        self.logger.info(
            "Verifying that the correct exception was raised when publishing with a non-alive "
            "publisher."
        )
        self.assertEqual(str(cm.exception), "Publisher is not alive")
