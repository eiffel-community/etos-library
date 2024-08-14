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
"""Environment request custom resource manager ETOS."""
import logging
from .etos import Kubernetes, Resource


class EnvironmentRequest(Resource):
    """EnvironmentRequest handles the EnvironmentRequest custom Kubernetes resources."""

    logger = logging.getLogger(__name__)

    def __init__(self, client: Kubernetes, strict: bool = False):
        """Set up Kubernetes client.

        :param strict: If True, the client will raise exceptions when Kubernetes could not
        be reached as expected such as the ETOS namespace not being able to be determined.
        The default (False) will just ignore any problems.
        """
        self.strict = strict
        with self._catch_errors_if_not_strict():
            self.client = client.environment_requests
            self.namespace = client.namespace
