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
"""Models for the EnvironmentRequest resource."""
from typing import Optional
from pydantic import BaseModel
from .common import Metadata
from .testrun import Test

class Iut(BaseModel):
    id: str

class ExecutionSpace(BaseModel):
    id: str
    testRunner: str

class LogArea(BaseModel):
    id: str


class EnvironmentProviders(BaseModel):
    iut: Optional[Iut] = None
    executionSpace: Optional[ExecutionSpace] = None
    logArea: Optional[LogArea] = None


class Splitter(BaseModel):
    tests: list[Test]


class EnvironmentRequestSpec(BaseModel):
    """EnvironmentRequstSpec is the specification of an EnvironmentRequest Kubernetes resource."""
    id: str
    name: Optional[str] = None
    identifier: str
    image: str
    imagePullPolicy: str
    artifact: str
    identity: str
    minimumAmount: int
    maximumAmount: int
    dataset: Optional[dict] = None
    providers: EnvironmentProviders
    splitter: Splitter


class EnvironmentRequest(BaseModel):
    """EnvironmentRequest Kubernetes resource."""

    apiVersion: Optional[str] = "etos.eiffel-community.github.io/v1alpha1"
    kind: Optional[str] = "EnvironmentRequest"
    metadata: Metadata
    spec: EnvironmentRequestSpec
