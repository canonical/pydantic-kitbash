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
from re import M
from typing import Annotated, Any, cast

import pydantic
import pytest
from docutils import nodes
from docutils.core import publish_doctree
from docutils.statemachine import StringList
from pydantic_kitbash.directives import KitbashFieldDirective, strip_whitespace
from typing_extensions import override

LIST_TABLE_RST = """

.. list-table::
    :header-rows: 1

    * - Values
      - Description
    * - ``value1``
      - The first value.
    * - ``value2``
      - The second value.

"""


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
        examples=["str1", "str2", "str3"],
    ),
]


class MockEnum(enum.Enum):
    """Enum docstring."""

    VALUE_1 = "value1"
    """The first value."""

    VALUE_2 = "value2"
    """The second value."""


class MockModel(pydantic.BaseModel):
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
    typing_union: TEST_TYPE | None


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
        arguments = [fake_field_directive.__module__ + ".MockModel", value]
    elif value := overrides.get("arguments"):
        arguments = value
    else:
        arguments = [fake_field_directive.__module__ + ".MockModel", "mock_field"]

    return FakeFieldDirective(
        name=overrides.get("name", "kitbash-field"),
        arguments=arguments,
        options=overrides.get("options", {}),
        content=overrides.get("content", []),
    )


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "i_dont_exist"}],
    indirect=True,
)
def test_kitbash_field_invalid(fake_field_directive: FakeFieldDirective):
    with pytest.raises(ValueError, match="Could not find field: i_dont_exist"):
        fake_field_directive.run()


def test_kitbash_field(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node

    field_entry = """\

    .. important::

        Deprecated. ew.

    **Type**

    ``int``

    **Description**

    description

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    ("fake_field_directive", "title_text"),
    [
        pytest.param(
            {"options": {"prepend-name": "app"}}, "app.test", id="prepend-name"
        ),
        pytest.param({"options": {"append-name": "app"}}, "test.app", id="append-name"),
    ],
    indirect=["fake_field_directive"],
)
def test_kitbash_field_name_options(
    fake_field_directive: FakeFieldDirective, title_text: str
):
    expected = nodes.section(ids=[title_text])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text=title_text)
    expected += title_node

    field_entry = """\

    .. important::

        Deprecated. ew.

    **Type**

    ``int``

    **Description**

    description

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive", [{"options": {"override-type": "override"}}], indirect=True
)
def test_kitbash_field_override_type(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node

    field_entry = """\

    .. important::

        Deprecated. ew.

    **Type**

    ``override``

    **Description**

    description

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "bad_example", "options": {"skip-examples": None}}],
    indirect=True,
)
def test_kitbash_field_skip_examples(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["bad_example"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="bad_example")
    expected += title_node

    field_entry = """\

    **Type**

    ``int``

    **Description**

    description

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "enum_field"}],
    indirect=True,
)
def test_kitbash_field_enum(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["enum_field"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="enum_field")
    expected += title_node

    field_entry = """\

    **Type**

    ``MockEnum``

    **Description**

    Enum docstring.

    **Values**

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    table_container = nodes.container()
    table_container += publish_doctree(LIST_TABLE_RST).children
    expected += table_container

    actual = fake_field_directive.run()[0]
    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "uniontype_field"}],
    indirect=True,
)
def test_kitbash_field_union_type(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["uniontype_field"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="uniontype_field")
    expected += title_node

    field_entry = """\

    **Type**

    ``str``

    **Description**

    This is types.UnionType

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "enum_uniontype"}],
    indirect=True,
)
def test_kitbash_field_enum_union(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["enum_uniontype"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="enum_uniontype")
    expected += title_node

    field_entry = """\

    **Type**

    ``MockEnum``

    **Description**

    Enum docstring.

    **Values**

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    table_container = nodes.container()
    table_container += publish_doctree(LIST_TABLE_RST).children
    expected += table_container

    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "typing_union", "options": {"skip-examples": None}}],
    indirect=True,
)
def test_kitbash_field_typing_union(fake_field_directive: FakeFieldDirective):
    expected = nodes.section(ids=["typing_union"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="typing_union")
    expected += title_node

    field_entry = """\

    **Type**

    ``str``

    **Description**

    This is a typing.Union

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)
