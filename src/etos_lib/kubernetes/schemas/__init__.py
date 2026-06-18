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
"""ETOS Kubernetes schemas."""

# Defaulting to v1alpha1 as to not break existing users of the library.
# The v1beta1 schemas are available under the `v1beta1` submodule.
from .common import Metadata
from .v1alpha1.environment import *
from .v1alpha1.environment_request import *
from .v1alpha1.provider import *
from .v1alpha1.testrun import *
