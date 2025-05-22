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
from typing import Annotated, Any

import pydantic
import pytest
from docutils import nodes
from docutils.core import publish_doctree
from docutils.statemachine import StringList
from pydantic_kitbash.directives import KitbashModelDirective, strip_whitespace
from typing_extensions import override

MOCK_FIELD_RST = """\

.. important::

    Deprecated. ew.

**Type**

``int``

**Description**

description

"""

UNIONTYPE_RST = """\

**Type**

``str``

**Description**

This is types.UnionType

"""

TYPING_UNION_RST = """\

**Type**

``str``

**Description**

This is a typing.Union

"""

ENUM_RST = """\

**Type**

``MockEnum``

**Description**

Enum docstring.

**Values**

"""

ENUM_UNION_RST = """\

**Type**

``MockEnum``

**Description**

Enum docstring.

**Values**

"""

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


def validator(value: str) -> str:
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


@pytest.mark.parametrize(
    "fake_model_directive", [{"model": ".OopsNoModel"}], indirect=True
)
def test_kitbash_model_invalid(fake_model_directive):
    assert fake_model_directive.run() == []


def test_kitbash_model(fake_model_directive):
    expected = list(publish_doctree(MockModel.__doc__).children)

    uniontype_section = nodes.section(ids=["uniontype_field"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="uniontype_field")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["enum_field"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="enum_field")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["enum_uniontype"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="enum_uniontype")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["typing_union"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="typing_union")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_model_directive",
    [
        {
            "options": {
                "skip-description": None,
            }
        }
    ],
    indirect=True,
)
def test_kitbash_model_skip_description(fake_model_directive):
    expected = []

    uniontype_section = nodes.section(ids=["uniontype_field"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="uniontype_field")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["enum_field"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="enum_field")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["enum_uniontype"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="enum_uniontype")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["typing_union"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="typing_union")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_model_directive", [{"content": ["``Test content``"]}], indirect=True
)
def test_kitbash_model_content(fake_model_directive):
    expected = list(publish_doctree("``Test content``").children)

    uniontype_section = nodes.section(ids=["uniontype_field"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="uniontype_field")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["enum_field"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="enum_field")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["enum_uniontype"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="enum_uniontype")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["typing_union"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="typing_union")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_model_directive",
    [
        {
            "options": {
                "include-deprecated": "mock_field",
            }
        }
    ],
    indirect=True,
)
def test_kitbash_model_include_deprecated(fake_model_directive):
    expected = list(publish_doctree("this is the model's docstring").children)

    mock_field_section = nodes.section(ids=["test"])
    mock_field_section["classes"].append("kitbash-entry")
    mock_field_title = nodes.title(text="test")
    mock_field_section += mock_field_title

    mock_field_rst = strip_whitespace(MOCK_FIELD_RST)
    mock_field_section += publish_doctree(mock_field_rst).children
    expected.append(mock_field_section)

    uniontype_section = nodes.section(ids=["uniontype_field"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="uniontype_field")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["enum_field"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="enum_field")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["enum_uniontype"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="enum_uniontype")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["typing_union"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="typing_union")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_model_directive",
    [
        {
            "options": {
                "prepend-name": "prefix",
            }
        }
    ],
    indirect=True,
)
def test_kitbash_model_prepend_name(fake_model_directive):
    expected = list(publish_doctree("this is the model's docstring").children)

    uniontype_section = nodes.section(ids=["prefix.uniontype_field"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="prefix.uniontype_field")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["prefix.enum_field"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="prefix.enum_field")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["prefix.enum_uniontype"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="prefix.enum_uniontype")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["prefix.typing_union"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="prefix.typing_union")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_model_directive",
    [
        {
            "options": {
                "append-name": "suffix",
            }
        }
    ],
    indirect=True,
)
def test_kitbash_model_append_name(fake_model_directive):
    expected = list(publish_doctree("this is the model's docstring").children)

    uniontype_section = nodes.section(ids=["uniontype_field.suffix"])
    uniontype_section["classes"].append("kitbash-entry")
    uniontype_title = nodes.title(text="uniontype_field.suffix")
    uniontype_section += uniontype_title

    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = nodes.section(ids=["enum_field.suffix"])
    enum_section["classes"].append("kitbash-entry")
    enum_title = nodes.title(text="enum_field.suffix")
    enum_section += enum_title

    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children

    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = nodes.section(ids=["enum_uniontype.suffix"])
    enum_uniontype_section["classes"].append("kitbash-entry")
    enum_uniontype_title = nodes.title(text="enum_uniontype.suffix")
    enum_uniontype_section += enum_uniontype_title

    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = nodes.section(ids=["typing_union.suffix"])
    typing_union_section["classes"].append("kitbash-entry")
    typing_union_title = nodes.title(text="typing_union.suffix")
    typing_union_section += typing_union_title

    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    assert str(expected) == str(actual)
