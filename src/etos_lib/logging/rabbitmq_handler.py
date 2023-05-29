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
"""ETOS rabbitmq handler."""
import json
import logging


class RabbitMQHandler(logging.StreamHandler):
    """A RabbitMQ log handler that sends logs tagged with user_log to RabbitMQ.

    Example::

        import logging
        from uuid import uuid4
        from etos_lib.logging.logger import setup_logging, FORMAT_CONFIG

        FORMAT_CONFIG.identifier = str(uuid4())
        setup_logging("myApp", "1.0.0", "production")
        logger = logging.getLogger(__name__)
        logger.info("Hello!", extra={"user_log": True})
    """

    closing = False

    def __init__(self, rabbitmq):
        """Initialize."""
        super().__init__()
        self.rabbitmq = rabbitmq

    def emit(self, record):
        """Send user log to RabbitMQ, starting the connection if necessary.

        The record parameter "user_log" must be set to True if a message shall be
        sent to RabbitMQ.
        """
        if self.closing:
            return

        try:
            send = record.user_log
        except AttributeError:
            send = False

        msg = self.format(record)
        try:
            identifier = record.identifier
        except AttributeError:
            identifier = json.loads(msg).get("identifier", "Unknown")
        # An unknown identifier will never be picked up by user log handler
        # so it is unnecessary to send it.
        routing_key = f"{identifier}.log.{record.levelname}"
        if send and self.rabbitmq.is_alive():
            if identifier == "Unknown":
                raise ValueError("Trying to send a user log when identifier is not set")
            self.rabbitmq.send_event(msg, routing_key=routing_key)
