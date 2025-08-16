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
"""ETOS publisher interface."""

from .events import Event


class Publisher:
    """Publisher interface for ETOS."""

    def publish(self, testrun_id: str, event: Event):
        """Publish an event to the internal messagebus."""
        raise NotImplementedError

    def start(self):
        """Start the connection to the server."""
        raise NotImplementedError

    def close(self):
        """Close the connection to the server."""
        raise NotImplementedError

    def is_alive(self):
        """Check if the connection is alive."""
        raise NotImplementedError
