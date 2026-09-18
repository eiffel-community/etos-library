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
"""Tests for the serialization of messaging events."""

import json
import unittest

from etos_lib.messaging.events import Message, Status, parse
from etos_lib.messaging.publisher import serialize_event
from etos_lib.messaging.types import Log, ServiceHealth, ServiceStatus


class TestMessageSerialization(unittest.TestCase):
    """Test that message log events serialize the timestamp to '@timestamp'."""

    def test_serializes_timestamp_as_at_timestamp(self):
        """Test that a message serializes the timestamp under the '@timestamp' key."""
        # A log record provides the timestamp as '@timestamp'.
        log = Log(
            **{
                "message": "hello",
                "name": "etos",
                "levelname": "info",
                "@timestamp": "2026-09-03T10:00:00Z",
            }
        )
        data = json.loads(Message(data=log).model_dump_json())["data"]
        self.assertIn("@timestamp", data)
        self.assertNotIn("datestring", data)

    def test_round_trip(self):
        """Test that a serialized message parses back without leaking the alias into extras."""
        log = Log(
            **{
                "message": "hello",
                "name": "etos",
                "levelname": "info",
                "@timestamp": "2026-09-03T10:00:00Z",
            }
        )
        body = Message(data=log).model_dump_json()
        event = parse(json.loads(body))
        data = event.model_dump()["data"]
        self.assertIn("@timestamp", data)
        self.assertNotIn("datestring", data)

    def test_publisher_omits_unset_event_id(self):
        """Test that publisher serialization does not encode an unset event ID as null."""
        event = Status(
            data=ServiceStatus(
                name="test-runner",
                instance="test-runner-0",
                version="1.0.0",
                status=ServiceHealth.OK,
            )
        )

        serialized = json.loads(serialize_event(event))

        self.assertNotIn("id", serialized)
        self.assertEqual(serialized["event"], "status")
        self.assertEqual(serialized["meta"], "test-runner")


if __name__ == "__main__":
    unittest.main()
