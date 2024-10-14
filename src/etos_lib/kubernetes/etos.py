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
"""Kubernetes client for ETOS custom resources."""
import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from kubernetes import config
from kubernetes.client import api_client
from kubernetes.dynamic import DynamicClient
from kubernetes.dynamic.resource import Resource as DynamicResource, ResourceInstance
from kubernetes.dynamic.exceptions import NotFoundError

config.load_config()
NAMESPACE_FILE = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")


class NoNamespace(Exception):
    """NoNamespace exception is raised when ETOS could not determine the current namespace."""


class Resource:
    """Resource is the base resource client for ETOS custom resources.

    This resource base class is used by our custom resources to, somewhat, mimic
    the behavior of a built-in resource from Kubernetes. This means that we don't
    do any error handling as that is not done in the built-in Kubernetes client.

    While we do somewhat mimic the behavior we don't necessarily mimic the "API"
    of the built-in resources. For example, we return boolean where the built-in
    would return the Kubernetes API response. We do this because of how we typically
    use Kubernetes in our services. If the Kubernetes API response is preferred
    we can still use the client :obj:`DynamicResource` directly.
    """

    client: DynamicResource
    namespace: str = "default"

    def get(self, name: str) -> Optional[ResourceInstance]:
        """Get a resource from Kubernetes by name."""
        return self.client.get(name=name, namespace=self.namespace)  # type: ignore

    def delete(self, name: str) -> bool:
        """Delete a resource by name."""
        if self.client.delete(name=name, namespace=self.namespace):  # type: ignore
            return True
        return False

    def create(self, model: BaseModel) -> bool:
        """Create a resource from a pydantic model."""
        if self.client.create(body=model.model_dump(), namespace=self.namespace):  # type: ignore
            return True
        return False

    def exists(self, name: str) -> bool:
        """Test if a resource with name exists."""
        try:
            return self.get(name) is not None
        except NotFoundError:
            return False


class Kubernetes:
    """Kubernetes is a client for fetching ETOS custom resources from Kubernetes."""

    __providers = None
    __requests = None
    __testruns = None
    __environments = None
    __namespace = None
    logger = logging.getLogger(__name__)

    def __init__(self, version="v1alpha1"):
        """Initialize a dynamic client with version."""
        self.version = f"etos.eiffel-community.github.io/{version}"
        self.__client = DynamicClient(api_client.ApiClient())

    @property
    def namespace(self) -> str:
        """Namespace returns the current namespace of the machine this code is running on."""
        if self.__namespace is None:
            if not NAMESPACE_FILE.exists():
                self.logger.warning(
                    "Not running in Kubernetes? Namespace file not found: %s", NAMESPACE_FILE
                )
                etos_ns = os.getenv("ETOS_NAMESPACE")
                if etos_ns:
                    self.logger.warning(
                        "Defauling to environment variable 'ETOS_NAMESPACE': %s", etos_ns
                    )
                else:
                    self.logger.warning("ETOS_NAMESPACE environment variable not set!")
                    raise NoNamespace("Failed to determine Kubernetes namespace!")
                self.__namespace = etos_ns
            else:
                self.__namespace = NAMESPACE_FILE.read_text(encoding="utf-8")
        return self.__namespace

    @property
    def providers(self) -> DynamicResource:
        """Providers request returns a client for Provider resources."""
        if self.__providers is None:
            self.__providers = self.__client.resources.get(
                api_version=self.version, kind="Provider"
            )
        return self.__providers

    @property
    def environment_requests(self) -> DynamicResource:
        """Environment requests returns a client for EnvironmentRequest resources."""
        if self.__requests is None:
            self.__requests = self.__client.resources.get(
                api_version=self.version, kind="EnvironmentRequest"
            )
        return self.__requests

    @property
    def environments(self) -> DynamicResource:
        """Environments returns a client for Environment resources."""
        if self.__environments is None:
            self.__environments = self.__client.resources.get(
                api_version=self.version, kind="Environment"
            )
        return self.__environments

    @property
    def testruns(self) -> DynamicResource:
        """Testruns returns a client for TestRun resources."""
        if self.__testruns is None:
            self.__testruns = self.__client.resources.get(api_version=self.version, kind="TestRun")
        return self.__testruns
