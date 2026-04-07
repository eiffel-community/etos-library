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
"""Types used by events but are not events themselves."""

from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints


class File(BaseModel):
    """An ETOS file event."""

    url: str
    name: str
    directory: str | None = None
    checksums: dict = {}


class Log(BaseModel):
    """An ETOS log."""

    # Log describes all the required fields for a log message, but when running in python we get
    # a ton of other key/value pairs that give extra context if wanted, setting extra='allow' will
    # make sure that these extra fields are also published.
    model_config = ConfigDict(extra="allow")

    message: str
    level: Annotated[str, StringConstraints(to_lower=True)] = Field("info", alias="levelname")
    name: str
    # The datestring field is, by default, generated as '@timestamp' but since
    # that is illegal in python we convert the name over to 'datestring'. Using
    # an aliased Field.
    # The '@timestamp' key is necessary for logstash, which we support, so we
    # cannot update the formatter that creates the '@timestamp' key.
    datestring: datetime = Field(
        serialization_alias="datestring", validation_alias=AliasChoices("@timestamp", "datestring")
    )


class Result(BaseModel):
    """Shutdown result."""

    conclusion: str
    verdict: str
    description: str = ""
