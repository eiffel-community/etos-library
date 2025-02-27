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
"""ETOS internal messaging events."""

import inspect
import sys
from typing import Optional, Any
from pydantic import BaseModel, Field
from .types import File, Log, Result


class Event(BaseModel):
    """Base internal messaging event."""

    id: Optional[int] = None
    event: str = "Unknown"
    data: Any
    meta: str = "*"

    def __str__(self) -> str:
        """Return the string representation of an event."""
        return f"{self.event}({self.id}): {self.data}"

    def __eq__(self, other: "Event") -> bool:  # type:ignore
        """Check if the event is the same by testing the IDs."""
        if self.id is None or other.id is None:
            return super().__eq__(other)
        return self.id == other.id


class ServerEvent(Event):
    """Events to be handled by the client."""


class UserEvent(Event):
    """Events to be handled by the user."""


class Ping(ServerEvent):
    """A ping event. Sent to keep connection between server and client alive."""

    event: str = "Ping"
    data: Any = None


class Error(ServerEvent):
    """An error from the messaging server."""

    event: str = "Error"
    data: Any = None


class Unknown(UserEvent):
    """An unknown event."""

    event: str = "Unknown"
    data: Any = None


class Shutdown(UserEvent):
    """A shutdown event from ETOS."""

    event: str = "Shutdown"
    data: Result

    def __str__(self) -> str:
        """Return the string representation of a shutdown."""
        return (
            f"Result(conclusion={self.data.conclusion}, "
            f"verdict={self.data.verdict}, description={self.data.description})"
        )


class Message(UserEvent):
    """An ETOS user log event."""

    event: str = "Message"
    data: Log
    meta: str = Field(default_factory=lambda data: data["data"].level)

    def __str__(self) -> str:
        """Return the string representation of a user log."""
        return self.data.message


class Report(UserEvent):
    """An ETOS test case report file event."""

    event: str = "Report"
    data: File

    def __str__(self) -> str:
        """Return the string representation of a file."""
        return f"[{self.data.name}]({self.data.url})"


class Artifact(UserEvent):
    """An ETOS test case artifact file event."""

    event: str = "Artifact"
    data: File

    def __str__(self) -> str:
        """Return the string representation of a file."""
        return f"[{self.data.name}]({self.data.url})"


def parse(event: dict) -> Event:
    """Parse an event dict and return a corresponding Event class."""
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if event.get("event", "").lower() == name.lower():
            return obj.model_validate(event)
    return Unknown(**event)
