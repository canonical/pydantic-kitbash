# This file is part of pydantic-kitbash.
#
# Copyright 2025 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License version 3, as published by the Free
# Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranties of MERCHANTABILITY, SATISFACTORY
# QUALITY, or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import enum
from pathlib import Path
from typing import Annotated, Any

import pydantic
import pytest
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from docutils.parsers.rst.states import RSTState, RSTStateMachine
from docutils.statemachine import StringList
from docutils.utils import new_document
from pydantic_kitbash.directives import KitbashFieldDirective, KitbashModelDirective
from sphinx.environment import BuildEnvironment
from sphinx.testing.util import SphinxTestApp
from typing_extensions import override

### Directive fixtures ###


class FakeFieldDirective(KitbashFieldDirective):
    """An override for testing only our additions."""

    @override
    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, Any],
        content: StringList,
        env_root: Path,
    ):
        self.name = name
        self.arguments = arguments
        self.options = options
        self.content = content
        self.state = mock_state(env_root)


@pytest.fixture
def fake_field_directive(
    request: pytest.FixtureRequest, tmp_path
) -> FakeFieldDirective:
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
        env_root=tmp_path,
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
        env_root: Path,
    ):
        self.name = name
        self.arguments = arguments
        self.options = options
        self.content = content
        self.state = mock_state(env_root)


@pytest.fixture
def fake_model_directive(
    request: pytest.FixtureRequest, tmp_path
) -> FakeModelDirective:
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
        env_root=tmp_path,
    )


### Mock Sphinx application instance ###


def mock_state(tmp_path) -> RSTState:
    state_machine = RSTStateMachine([], "")
    state = RSTState(state_machine)
    document = new_document("docname", settings=get_default_settings(Parser))

    src_dir = tmp_path / "src"

    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "conf.py").write_text("project = 'mock'")
    (src_dir / "index.rst").write_text("index\n=====")

    test_app = SphinxTestApp(srcdir=src_dir)
    test_app.build()

    build_env = BuildEnvironment(test_app)
    build_env.temp_data["docname"] = "index"

    document.settings.env = build_env
    state.document = document

    return state


### Models and types for test input ###


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
    no_desc: str = pydantic.Field(alias="no-desc")
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
