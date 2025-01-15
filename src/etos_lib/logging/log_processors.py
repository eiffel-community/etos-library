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
"""Custom log processors for use with Open Telemetry logging signals."""

from opentelemetry.sdk._logs import LogData, LogRecordProcessor


class ToStringProcessor(LogRecordProcessor):
    """Simple log record processor to convert all log records to type string."""

    def emit(self, log_data: LogData) -> None:
        """Change record body to string and emit the `LogData`."""
        record = log_data.log_record
        if not isinstance(record.body, (str, bool, int, float)):
            record.body = str(record.body)

    def force_flush(self, _timeout_millis: int = 30000) -> bool:
        """Export all the received, but not yet exported, logs to the configured Exporter."""
        return True

    def shutdown(self) -> None:
        """Logger shutdown procedures."""
