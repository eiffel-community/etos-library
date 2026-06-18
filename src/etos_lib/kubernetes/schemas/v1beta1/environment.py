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
"""Models for the v1beta1 Environment resource."""

from typing import Optional

from pydantic import BaseModel

from etos_lib.schemas.v0.environment import Suite as V0Suite

from ..common import Metadata
from .testrun import Providers, TestExecution

__all__ = ["Environment", "EnvironmentSpec", "EnvironmentStatus"]


class EnvironmentSpec(BaseModel):
    """EnvironmentSpec is the specification of a Environment Kubernetes resource."""

    name: str
    id: str
    testrunID: str
    mainSuiteID: str
    artifact: str
    context: str
    testRunner: str
    providers: Providers
    iut: dict
    executor: dict
    logArea: dict
    priority: int = 1
    deadline: int = 0
    testExecutions: list[TestExecution]
    dataset: Optional[dict] = None

    @classmethod
    def convert_from(cls, src: V0Suite) -> "EnvironmentSpec":
        """Convert V0Suite to EnvironmentSpec."""
        return cls(
            artifact=src.artifact,
            context=src.context,
            executor=src.executor,
            iut=src.iut,
            logArea=src.log_area,
            name=src.name,
            priority=src.priority,
            testExecutions=[TestExecution.convert_from(test) for test in src.recipes],
            id=src.sub_suite_id,
            testrunID=src.suite_id,
            testRunner=src.test_runner,
            mainSuiteID=src.test_suite_started_id,
            providers=Providers(
                iut="Unknown",
                executionSpace="Unknown",
                logArea="Unknown",
            ),
        )

    def convert_to(self) -> V0Suite:
        """Convert EnvironmentSpec to V0Suite."""
        return V0Suite(
            artifact=self.artifact,
            context=self.context,
            executor=self.executor,
            iut=self.iut,
            log_area=self.logArea,
            name=self.name,
            priority=self.priority,
            recipes=[test.convert_to() for test in self.testExecutions],
            sub_suite_id=self.id,
            suite_id=self.testrunID,
            test_runner=self.testRunner,
            test_suite_started_id=self.mainSuiteID,
        )


class EnvironmentStatus(BaseModel):
    """EnvironmentStatus describes the observed state of a Environment resource."""

    completionTime: Optional[str] = None


class Environment(BaseModel):
    """Environment Kubernetes resource."""

    apiVersion: Optional[str] = "etos.eiffel-community.github.io/v1beta1"
    kind: Optional[str] = "Environment"
    metadata: Metadata
    spec: EnvironmentSpec
    status: Optional[EnvironmentStatus] = None
