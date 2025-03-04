# Copyright 2020-2021 Axis Communications AB.
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
"""ETOS Library module."""

import time
from etos_lib.messaging.publisher import Publisher
from etos_lib.messaging.v1.publisher import Publisher as V1Publisher
from etos_lib.messaging.v2alpha.publisher import Publisher as V2alphaPublisher
from .eiffel.publisher import TracingRabbitMQPublisher as RabbitMQPublisher
from .eiffel.subscriber import TracingRabbitMQSubscriber as RabbitMQSubscriber
from .graphql.query_handler import GraphQLQueryHandler
from .lib.config import Config
from .lib.debug import Debug
from .lib.events import Events
from .lib.exceptions import (
    PublisherConfigurationMissing,
    PublisherNotStarted,
    SubscriberConfigurationMissing,
)
from .lib.feature_flags import FeatureFlags
from .lib.http import Http
from .lib.monitor import Monitor
from .lib.utils import Utils


class ETOS:  # pylint: disable=too-many-instance-attributes
    """ETOS Library."""

    publisher = None
    subscriber = None
    __config = None
    __events = None
    __monitor = None
    __utils = None
    __graphql = None
    __http = None
    __debug = None
    __feature_flags = None

    def __init__(self, service_name, host, name, domain_id=None):
        """Initialize source and service name."""
        source = {"name": name, "host": host}
        if domain_id is not None:
            source["domainId"] = domain_id
        self.config.set("source", source)
        self.config.set("service_name", service_name)

    def __del__(self):
        """Delete references to eiffel publisher and subscriber."""
        self.config.set("publisher", None)
        self.config.set("subscriber", None)

    def start_publisher(self):
        """Start the RabbitMQ publisher using config data from ETOS library config service."""
        rabbitmq = self.config.get("rabbitmq_publisher")
        if not rabbitmq:
            raise PublisherConfigurationMissing
        self.publisher = RabbitMQPublisher(routing_key=None, **rabbitmq)
        if not self.debug.disable_sending_events:
            self.publisher.start()
        self.config.set("publisher", self.publisher)

    def start_subscriber(self):
        """Start the RabbitMQ subscriber using config data from ETOS library config service."""
        rabbitmq = self.config.get("rabbitmq_subscriber")
        if not rabbitmq:
            raise SubscriberConfigurationMissing
        self.subscriber = RabbitMQSubscriber(**rabbitmq)
        if not self.debug.disable_receiving_events:
            self.subscriber.start()
        self.config.set("subscriber", self.subscriber)

    def messagebus_publisher(self, version: str = "v1") -> Publisher:
        """Start the internal messagebus publisher using config data from ETOS library.

        :param version: Version of the messagebus protocol to use.
        """
        publisher = self.config.get("internal_publisher")
        if publisher is None:
            connection_parameters = self.config.etos_rabbitmq_publisher_data()
            if not connection_parameters:
                raise PublisherConfigurationMissing
            if version == "v1":
                publisher = V1Publisher(**connection_parameters)
            elif version == "v2alpha":
                publisher = V2alphaPublisher(
                    self.config.etos_rabbitmq_publisher_uri(),
                    self.config.etos_stream_name(),
                )
            else:
                raise ValueError(f"Unknown version {version!r} of messagebus")
            if not self.debug.disable_sending_events:
                publisher.start()
                # Wait for start.
                # No timeout necessary since there is a built-in timeout in the publisher.
                while publisher.is_alive():
                    time.sleep(0.1)
            self.config.set("internal_publisher", publisher)
        return publisher

    @property
    def debug(self):
        """Entry for debug parameters for ETOS."""
        if self.__debug is None:
            self.__debug = Debug()
        return self.__debug

    @property
    def feature_flags(self):
        """Entry for feature flags for ETOS."""
        if self.__feature_flags is None:
            self.__feature_flags = FeatureFlags()
        return self.__feature_flags

    @property
    def monitor(self):
        """Entry for ETOS Library monitor service."""
        if self.__monitor is None:
            self.__monitor = Monitor()
        return self.__monitor

    @property
    def events(self):
        """Entry for ETOS Library events service. Publisher must be started."""
        if self.__events is None:
            if self.publisher is None and not self.debug.disable_sending_events:
                raise PublisherNotStarted
            self.__events = Events(self.publisher)
        return self.__events

    @property
    def config(self):
        """Entry for ETOS Library config service."""
        if self.__config is None:
            self.__config = Config()
        return self.__config

    @property
    def utils(self):
        """Entry for ETOS Library utils service."""
        if self.__utils is None:
            self.__utils = Utils()
        return self.__utils

    @property
    def http(self):
        """Entry for ETOS Library http service."""
        if self.__http is None:
            self.__http = Http()
        return self.__http

    @property
    def graphql(self):
        """Entry for ETOS Library http service."""
        if self.__graphql is None:
            self.__graphql = GraphQLQueryHandler()
        return self.__graphql
