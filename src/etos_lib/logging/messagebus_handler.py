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
from etos_lib.messaging.publisher import Publisher
from etos_lib.messaging.v2alpha.publisher import Publisher as V2alphaPublisher
from etos_lib.messaging.events import Log, Message


class MessagebusHandler(logging.StreamHandler):
    """A log handler that sends logs tagged with user_log to the internal messagebus.

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

    def __init__(self, publisher: Publisher):
        """Initialize."""
        super().__init__()
        self.publisher = publisher

    def emit(self, record: logging.LogRecord):
        """Send user log to messagebus.

        The record parameter "user_log" must be set to True if a message shall be sent.
        """
        if self.closing:
            return
        try:
            send = record.user_log
        except AttributeError:
            # If it's the v2alpha protocol, always set to True unless explicitly
            # disabled with `user_log=False`.
            send = isinstance(self.publisher, V2alphaPublisher)
        if not send:
            return

        msg = self.format(record)
        if not isinstance(msg, dict):
            msg = json.loads(msg)

        try:
            identifier = record.identifier
        except AttributeError:
            identifier = msg.get("identifier")
        if identifier is None or identifier == "Unknown":
            return

        if self.publisher.is_alive():
            self.publisher.publish(identifier, Message(data=Log(**msg)))
