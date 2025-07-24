import enum
from typing import Annotated, Any

import pydantic
import pytest
from docutils.statemachine import StringList
from pydantic_kitbash.directives import KitbashFieldDirective, KitbashModelDirective
from typing_extensions import override


class FakeFieldDirective(KitbashFieldDirective):
    """An override for testing only our additions."""

    @override
    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, Any],
        content: StringList,
    ):
        self.name = name
        self.arguments = arguments
        self.options = options
        self.content = content


@pytest.fixture
def fake_field_directive(request: pytest.FixtureRequest) -> FakeFieldDirective:
    """This fixture can be parametrized to override the default values.

    Most parameters are 1:1 with the init function of FakeFieldDirective, but
    there is one exception - the "model_field" key can be used as a shorthand
    to more easily select a field on the MockModel in this file instead of
    passing a fully qualified module name.
    """
    # Get any optional overrides from the fixtures
    overrides = request.param if hasattr(request, "param") else {}

    # Handle the model_field shorthand
    if value := overrides.get("model_field"):
        arguments = [fake_field_directive.__module__ + ".MockFieldModel", value]
    elif value := overrides.get("arguments"):
        arguments = value
    else:
        arguments = [fake_field_directive.__module__ + ".MockFieldModel", "mock_field"]

    return FakeFieldDirective(
        name=overrides.get("name", "kitbash-field"),
        arguments=arguments,
        options=overrides.get("options", {}),
        content=overrides.get("content", []),
    )


class FakeModelDirective(KitbashModelDirective):
    """An override for testing only our additions."""

    @override
    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, Any],
        content: StringList,
    ):
        self.name = name
        self.arguments = arguments
        self.options = options
        self.content = content


@pytest.fixture
def fake_model_directive(request: pytest.FixtureRequest) -> FakeModelDirective:
    """This fixture can be parametrized to override the default values.

    Most parameters are 1:1 with the init function of FakeModelDirective, but
    there is one exception - the "model_field" key can be used as a shorthand
    to more easily select a field on the MockModel in this file instead of
    passing a fully qualified module name.
    """
    # Get any optional overrides from the fixtures
    overrides = request.param if hasattr(request, "param") else {}

    # Handle the model_field shorthand
    if value := overrides.get("model"):
        arguments = [fake_model_directive.__module__ + value]
    elif value := overrides.get("arguments"):
        arguments = value
    else:
        arguments = [fake_model_directive.__module__ + ".MockModel"]

    return FakeModelDirective(
        name=overrides.get("name", "kitbash-model"),
        arguments=arguments,
        options=overrides.get("options", {}),
        content=overrides.get("content", []),
    )


def validator(
    value: str,
) -> str:
    return value.strip()


TEST_TYPE = Annotated[
    str,
    pydantic.AfterValidator(validator),
    pydantic.BeforeValidator(validator),
    pydantic.Field(
        description="This is a typing.Union",
    ),
]


TEST_TYPE_EXAMPLES = Annotated[
    str,
    pydantic.AfterValidator(validator),
    pydantic.BeforeValidator(validator),
    pydantic.Field(
        description="This is a typing.Union",
        examples=["str1", "str2", "str3"],
    ),
]


class MockEnum(enum.Enum):
    """Enum docstring."""

    VALUE_1 = "value1"
    """The first value."""

    VALUE_2 = "value2"
    """The second value."""


class MockFieldModel(pydantic.BaseModel):
    """Mock model for testing the kitbash-field directive"""

    mock_field: int = pydantic.Field(
        description="description",
        alias="test",
        deprecated="ew.",
    )
    bad_example: int = pydantic.Field(
        description="description",
        examples=["not good"],
    )
    uniontype_field: str | None = pydantic.Field(
        description="This is types.UnionType",
    )
    enum_field: MockEnum
    enum_uniontype: MockEnum | None
    typing_union: TEST_TYPE_EXAMPLES | None


class MockModel(pydantic.BaseModel):
    """this is the model's docstring"""

    mock_field: int = pydantic.Field(
        description="description",
        alias="test",
        deprecated="ew.",
    )
    uniontype_field: str | None = pydantic.Field(
        description="This is types.UnionType",
    )
    enum_field: MockEnum
    enum_uniontype: MockEnum | None
    typing_union: TEST_TYPE | None


class OopsNoModel:
    field1: int
