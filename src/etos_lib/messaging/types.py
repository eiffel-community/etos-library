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
from typing import Optional
from typing_extensions import Annotated
from pydantic import AliasChoices, BaseModel, Field, StringConstraints


class File(BaseModel):
    """An ETOS file event."""

    url: str
    name: str
    directory: Optional[str] = None
    checksums: dict = {}


class Log(BaseModel):
    """An ETOS log."""

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
