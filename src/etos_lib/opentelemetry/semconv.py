# Copyright 2020 Axis Communications AB.
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
"""ETOS OpenTelemetry semantic conventions module."""

class Attributes:
    """Constants for ETOS OpenTelemetry semantic conventions."""

    # General ETOS conventions
    SUITE_ID = "etos.suite.id"
    SUBSUITE_ID = "etos.subsuite.id"
    TESTRUN_ID = "etos.testrun.id"

    # Testrunner conentions
    TESTRUNNER_ID = "etos.testrunner.id"

    # Environment generic conventions
    ENVIRONMENT = "etos.subsuite.environment"  # environment description as JSON
    ENVIRONMENT_ID = "etos.environment.id"

    # Execution space conventions
    EXECUTOR_ID = "etos.environment.execution_space.executor.id"

    # IUT conventions
    IUT_DESCRIPTION = "etos.environment.iut.description" 
