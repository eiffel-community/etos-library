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
"""Models for the v0 suite."""

from typing import Optional, Union

from pydantic import (BaseModel, ValidationError, conlist, constr,
                      field_validator)
from pydantic.fields import PrivateAttr


class Environment(BaseModel):
    """ETOS suite definion 'ENVIRONMENT' constraint."""

    key: str
    value: dict


class Command(BaseModel):
    """ETOS suite definion 'COMMAND' constraint."""

    key: str
    value: constr(min_length=1)


class Checkout(BaseModel):
    """ETOS suite definion 'CHECKOUT' constraint."""

    key: str
    value: conlist(str, min_length=0)


class Parameters(BaseModel):
    """ETOS suite definion 'PARAMETERS' constraint."""

    key: str
    value: dict


class Execute(BaseModel):
    """ETOS suite definion 'EXECUTE' constraint."""

    key: str
    value: list[str]


class TestRunner(BaseModel):
    """ETOS suite definion 'TEST_RUNNER' constraint."""

    key: str
    value: constr(min_length=1)


class TestCase(BaseModel):
    """ETOS suite definion 'testCase' field."""

    id: str
    tracker: Optional[str] = None
    url: Optional[str] = None


class Constraint(BaseModel):
    """ETOS suite definion 'constraints' field."""

    key: str
    value: Union[str, list, dict]  # pylint:disable=unsubscriptable-object


class Recipe(BaseModel):
    """ETOS suite definion 'recipes' field."""

    constraints: list[Constraint]
    id: str
    testCase: TestCase

    __constraint_models = PrivateAttr(
        {
            "ENVIRONMENT": Environment,
            "COMMAND": Command,
            "CHECKOUT": Checkout,
            "PARAMETERS": Parameters,
            "EXECUTE": Execute,
            "TEST_RUNNER": TestRunner,
        }
    )

    @field_validator("constraints")
    def validate_constraints(cls, value):  # Pydantic requires cls. pylint:disable=no-self-argument
        """Validate the constraints fields for each recipe.

        Validation is done manually because error messages from pydantic
        are not clear enough when using a Union check on the models.
        Pydantic does not check the number of unions either, which is something
        that is required for ETOS.

        :raises ValueError: if there are too many or too few constraints.
        :raises TypeError: If an unknown constraint is detected.
        :raises ValidationError: If constraint model does not validate.

        :param value: The current constraint that is being validated.
        :type value: Any
        :return: Same as value, if validated.
        :rtype: Any
        """
        keys = cls.__constraint_models.default.keys()
        count = dict.fromkeys(keys, 0)
        for constraint in value:
            model = cls.__constraint_models.default.get(constraint.key)
            if model is None:
                keys = tuple(keys)
                raise TypeError(f"Unknown key {constraint.key}, valid keys: {keys}")
            try:
                model(**constraint.model_dump())
            except ValidationError as exception:
                raise ValueError(str(exception)) from exception
            count[constraint.key] += 1
        more_than_one = [key for key, number in count.items() if number > 1]
        if more_than_one:
            raise ValueError(f"Too many instances of keys {more_than_one}. Only 1 allowed.")
        missing = [key for key, number in count.items() if number == 0]
        if missing:
            raise ValueError(f"Too few instances of keys {missing}. At least 1 required.")
        return value


class Suite(BaseModel):
    """ETOS base suite definition."""

    artifact: str
    context: str
    executor: dict
    iut: dict
    log_area: dict
    name: str
    priority: int
    recipes: list[Recipe]
    sub_suite_id: str
    suite_id: str
    test_runner: str
    test_suite_started_id: str
