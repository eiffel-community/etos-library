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

import os
import ctypes
import logging
from pathlib import Path
from ..events import Event
from ..publisher import Publisher as PublisherInterface


LIBRARY_PATH = Path(os.getenv("BINDINGS", Path(__file__).parent)).joinpath("stream/client.so")


class Publisher(PublisherInterface):
    """Internal messaging publisher for ETOS.

    This publisher is running in a shared C library created from
    Go because the Python library that we have access to is not
    fast enough and we could not create reliable connections using
    it.

    start() - Start up the publisher
    publish() - Publish an event
    close() - Stop the publisher and wait for outstanding events.
    is_alive() - Check if publisher is alive.

    Example usage:

        # Make sure that the ETOS_RABBITMQ_* and ETOS_STREAM_NAME environment variables are set.
        from etos_lib.etos import ETOS as ETOS_LIBRARY
        from etos_lib.messaging.protocol import Shutdown, Result
        ETOS = ETOS_LIBRARY(...)
        with ETOS.messagebus_publisher() as PUBLISHER:
            PUBLISHER.publish("identifier", Shutdown(data=Result(
                conclusion="SUCCESSFUL",
                verdict="PASSED",
                description="Hello world",
            )))

    Example usage with logger:

        # Make sure that the ETOS_RABBITMQ_* and ETOS_STREAM_NAME environment variables are set.
        import logging
        from etos_lib.logging.logger import setup_logging, FORMAT_CONFIG
        setup_logging("name", "version", "environment", None)
        FORMAT_CONFIG.identifier = "identifier"
        LOGGER = logging.getLogger(__name__)
        LOGGER.info("Hello world", extra={"user_log": True})
    """

    __connected = False
    logger = logging.getLogger(__name__)

    def __init__(self, connection_string: str, stream_name: str):
        """Initialize the Publisher object."""
        self.stream_name = stream_name
        self.__connection_string = connection_string
        self.__setup_bindings(LIBRARY_PATH)

    def __setup_bindings(self, library_path: Path):
        """Setup the bindings for the Publisher."""
        self.__library = ctypes.cdll.LoadLibrary(str(library_path))
        self.__handler = self.__library.New(
            self.__connection_string.encode("utf-8"),
            self.stream_name.encode("utf-8"),
        )
        self.__connect = self.__library.Publisher
        self.__connect.argtypes = [
            ctypes.c_int,  # pointer to stream handler
            ctypes.c_char_p,  # connectionString
            ctypes.c_char_p,  # streamName
        ]
        self.__publish = self.__library.Publish
        self.__publish.argtypes = [
            ctypes.c_int,  # pointer to stream handler
            ctypes.c_char_p,  # event
            ctypes.c_char_p,  # identifier
            ctypes.c_char_p,  # eventType
            ctypes.c_char_p,  # meta
        ]
        self.__close = self.__library.Close
        self.__close.argtypes = [ctypes.c_int]  # pointer to stream handler

    def __enter__(self):
        """Connect to the server."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the connection to the server."""
        self.close()

    def __del__(self):
        """Close the connection to the server."""
        self.close()

    def start(self):
        """Start the connection to the server."""
        if not self.__connected:
            success = self.__connect(
                self.__handler,
                self.__connection_string.encode("utf-8"),
                self.stream_name.encode("utf-8"),
            )
            if not success:
                raise Exception("Failed to connect to stream")
            self.__connected = True

    def publish(self, testrun_id: str, event: Event):
        """Publish an event to the internal messagebus."""
        assert self.__connected, "Not connected to the server"
        self.logger.debug(
            "Publishing event '%s' to id %r",
            event,
            testrun_id,
            extra={"user_log": False},
        )
        return self.__publish(
            self.__handler,
            event.model_dump_json().encode("utf-8"),
            testrun_id.encode("utf-8"),
            event.event.lower().encode("utf-8"),
            event.meta.encode("utf-8"),
        )

    def is_alive(self):
        """Check if the connection is alive."""
        return self.__connected

    def close(self):
        """Close the connection to the server."""
        if self.__connected:
            self.__close(self.__handler)
            self.__connected = False
            self.__handler = None
