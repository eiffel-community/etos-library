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
"""ETOS rabbitmq log publisher."""
import time
import json
import pika

from eiffellib.publishers import RabbitMQPublisher


class RabbitMQLogPublisher(RabbitMQPublisher):
    """A RabbitMQ publisher that can send JSON strings instead of Eiffel events."""

    def send_event(self, event, block=True, routing_key="#"):
        """Overload the send_event from the eiffellib rabbitmq publisher to send strings.

        This method differs slightly from its parent in that it takes the routing_key as input.
        """
        if block:
            self.wait_start()
            while self._channel is None or not self._channel.is_open:
                time.sleep(0.1)
        properties = pika.BasicProperties(content_type="application/json", delivery_mode=2)
        if not isinstance(event, str):
            event = json.dumps(event)

        with self._lock:
            try:
                self._channel.basic_publish(
                    self.exchange,
                    routing_key,
                    event,
                    properties,
                )
            except:  # pylint:disable=bare-except
                self._nacked_deliveries.append(event)
                return
            self._delivered += 1
            self._deliveries[self._delivered] = event
