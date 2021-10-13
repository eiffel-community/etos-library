# Copyright 2021 Axis Communications AB.
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
"""ETOS feature flags."""
import os

class FeatureFlags:
    """Feature flags for ETOS."""

    @property
    def disable_clm(self):
        """Whether or not CLM sending shall be disabled."""
        return os.getenv("ETOS_FEATURE_DISABLE_CLM", "false") == "true"