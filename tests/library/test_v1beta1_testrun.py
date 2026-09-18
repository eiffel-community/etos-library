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
"""Tests for v1beta1 TestRun models."""

from etos_lib.kubernetes.schemas.v1beta1.testrun import (
    Suite,
    TestExecution,
    TestRunStatus,
)
from etos_lib.schemas.v0.environment import Constraint, Recipe, TestCase


def test_convert_from_sorts_parameters():
    """Test that v0 parameters produce a deterministic v1beta1 command."""
    recipe = Recipe(
        id="test-execution",
        testCase=TestCase(id="test-case", tracker="tracker", url="https://example.com"),
        constraints=[
            Constraint(key="COMMAND", value="run-test"),
            Constraint(key="PARAMETERS", value={"zeta": "last", "alpha": "", "beta": "middle"}),
            Constraint(key="ENVIRONMENT", value={}),
            Constraint(key="CHECKOUT", value=[]),
            Constraint(key="EXECUTE", value=[]),
            Constraint(key="TEST_RUNNER", value="test-runner"),
        ],
    )

    converted = TestExecution.convert_from(recipe)

    assert converted.execution.command == "run-test alpha beta=middle zeta=last"


def test_suite_dataset_accepts_missing_null_and_object():
    """Test that optional v1beta1 datasets are not replaced with an empty object."""
    assert Suite(testExecutions=[]).dataset is None
    assert Suite(testExecutions=[], dataset=None).dataset is None
    assert Suite(testExecutions=[], dataset={"key": "value"}).dataset == {"key": "value"}
