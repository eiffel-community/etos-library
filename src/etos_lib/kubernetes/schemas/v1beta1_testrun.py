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
"""Models for the v1beta1 TestRun resource."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from .common import Image, Metadata

__all__ = ["TestRun", "TestRunSpec", "TestRunStatus"]


class TestCase(BaseModel):
    """TestCase describes a test case to run."""

    id: str
    tracker: Optional[str] = None
    uri: Optional[str] = None
    version: Optional[str] = None


class Execution(BaseModel):
    """Execution describes how to execute a test case."""

    command: str
    checkout: list[str] = []
    preExecution: list[str] = []


class AdditionalResource(BaseModel):
    """AdditionalResource describes an additional resource to be used in a test execution."""

    type: str
    model_config = ConfigDict(extra="allow")


class TestEnvironment(BaseModel):
    """TestEnvironment describes the environment in which a test shall run."""

    testRunner: str
    environmentVariables: dict[str, str] = {}
    additionalResources: list[AdditionalResource] = []


class TestExecution(BaseModel):
    """TestExecution describes how to execute a test case."""

    id: str
    testCase: TestCase
    execution: Execution
    environment: TestEnvironment
    dependencies: list[str] = []


class Suite(BaseModel):
    """Suite describes a test suite to run."""

    testExecutions: list[TestExecution]
    priority: int = 1
    dataset: dict = {}


class Retention(BaseModel):
    """Retention describes how long to keep the TestRun resources."""

    failure: Optional[int] = None
    success: Optional[int] = None


class Providers(BaseModel):
    """Providers describes the providers to use for a testrun."""

    executionSpace: Optional[str] = ""
    logArea: Optional[str] = ""
    iut: Optional[str] = ""


class TestRunner(BaseModel):
    """Test runner version."""

    version: str


class TestRunSpec(BaseModel):
    """TestRunSpec describes the desired state of a TestRun resource."""

    name: str
    artifact: str
    identity: str
    suites: list[Suite]
    providers: Providers
    suiteRunner: Optional[Image] = None
    environmentProvider: Optional[Image] = None
    testRunner: Optional[TestRunner] = None
    id: Optional[str] = None
    cluster: Optional[str] = None
    suiteSource: Optional[str] = None
    timeout: Optional[int] = None
    deadline: Optional[int] = None
    retention: Optional[Retention] = None
    schemaVersion: Optional[str] = "v1beta1"


class TestRunStatus(BaseModel):
    """TestRunStatus describes the observed state of a TestRun resource."""

    completionTime: Optional[str] = None
    verdict: Optional[str] = None


class TestRun(BaseModel):
    """TestRun Kubernetes resource."""

    apiVersion: Optional[str] = "etos.eiffel-community.github.io/v1beta1"
    kind: Optional[str] = "TestRun"
    metadata: Metadata
    spec: TestRunSpec
    status: Optional[TestRunStatus] = None
