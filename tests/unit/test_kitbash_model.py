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
from typing import Annotated

import pydantic
import pytest
from docutils import nodes
from docutils.core import publish_doctree
from pydantic_kitbash.directives import strip_whitespace

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

    * - Value
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
    ),
]


class MockEnum(enum.Enum):
    """Enum docstring."""

    VALUE_1 = "value1"
    """The first value."""

    VALUE_2 = "value2"
    """The second value."""


def build_section_node(title: str, node_id: str) -> nodes.section:
    """Create a section node containing all of the information for a single field.

    Args:
        node_id (str): The ref ID (label) for the field.
        title (str): The title node content (heading) for the field

    Returns:
        nodes.section: A section containing well-formed nodes for the field.

    """

    section_node = nodes.section(ids=[title, node_id])
    section_node["classes"].append("kitbash-entry")
    title_node = nodes.title(text=title)
    section_node += title_node
    target_node = nodes.target()
    target_node["refid"] = node_id
    section_node += target_node

    return section_node


def test_kitbash_model(fake_model_directive):
    """Test for the KitbashModelDirective."""

    expected = list(publish_doctree("this is the model's docstring").children)

    uniontype_section = build_section_node("uniontype_field", "docname-uniontype_field")
    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = build_section_node("enum_field", "docname-enum_field")
    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children
    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = build_section_node(
        "enum_uniontype", "docname-enum_uniontype"
    )
    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children
    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = build_section_node("typing_union", "docname-typing_union")
    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    for i, node in enumerate(expected):
        assert str(node) == str(actual[i])


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
    """Tests the skip-description option in KitbashModelDirective."""

    expected = []

    uniontype_section = build_section_node("uniontype_field", "docname-uniontype_field")
    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = build_section_node("enum_field", "docname-enum_field")
    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children
    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = build_section_node(
        "enum_uniontype", "docname-enum_uniontype"
    )
    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children

    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = build_section_node("typing_union", "docname-typing_union")
    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    for i, node in enumerate(expected):
        assert str(node) == str(actual[i])


@pytest.mark.parametrize(
    "fake_model_directive", [{"content": ["``Test content``"]}], indirect=True
)
def test_kitbash_model_content(fake_model_directive):
    """Tests the KitbashModelDirective when content is provided in the body."""

    expected = list(publish_doctree("``Test content``").children)

    uniontype_section = build_section_node("uniontype_field", "docname-uniontype_field")
    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = build_section_node("enum_field", "docname-enum_field")
    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children
    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = build_section_node(
        "enum_uniontype", "docname-enum_uniontype"
    )
    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children
    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = build_section_node("typing_union", "docname-typing_union")
    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    for i, node in enumerate(expected):
        assert str(node) == str(actual[i])


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
    """Tests the include-deprecated option in KitbashModelDirective."""

    expected = list(publish_doctree("this is the model's docstring").children)

    mock_field_section = build_section_node("test", "docname-test")
    mock_field_rst = strip_whitespace(MOCK_FIELD_RST)
    mock_field_section += publish_doctree(mock_field_rst).children
    expected.append(mock_field_section)

    uniontype_section = build_section_node("uniontype_field", "docname-uniontype_field")
    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = build_section_node("enum_field", "docname-enum_field")
    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children
    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = build_section_node(
        "enum_uniontype", "docname-enum_uniontype"
    )
    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children
    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = build_section_node("typing_union", "docname-typing_union")
    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    for i, node in enumerate(expected):
        assert str(node) == str(actual[i])


@pytest.mark.parametrize(
    "fake_model_directive",
    [
        {
            "options": {
                "prepend-name": "prefix",
                "append-name": "suffix",
            }
        }
    ],
    indirect=True,
)
def test_kitbash_model_name_options(fake_model_directive):
    """Tests the -name options in KitbashModelDirective."""

    expected = list(publish_doctree("this is the model's docstring").children)

    uniontype_section = build_section_node(
        "prefix.uniontype_field.suffix", "docname-uniontype_field"
    )
    uniontype_rst = strip_whitespace(UNIONTYPE_RST)
    uniontype_section += publish_doctree(uniontype_rst).children
    expected.append(uniontype_section)

    enum_section = build_section_node("prefix.enum_field.suffix", "docname-enum_field")
    enum_rst = strip_whitespace(ENUM_RST)
    enum_section += publish_doctree(enum_rst).children
    enum_value_container = nodes.container()
    enum_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_section += enum_value_container
    expected.append(enum_section)

    enum_uniontype_section = build_section_node(
        "prefix.enum_uniontype.suffix", "docname-enum_uniontype"
    )
    enum_uniontype_rst = strip_whitespace(ENUM_RST)
    enum_uniontype_section += publish_doctree(enum_uniontype_rst).children
    enum_uniontype_value_container = nodes.container()
    enum_uniontype_value_container += publish_doctree(LIST_TABLE_RST).children
    enum_uniontype_section += enum_uniontype_value_container
    expected.append(enum_uniontype_section)

    typing_union_section = build_section_node(
        "prefix.typing_union.suffix", "docname-typing_union"
    )
    typing_union_rst = strip_whitespace(TYPING_UNION_RST)
    typing_union_section += publish_doctree(typing_union_rst).children
    expected.append(typing_union_section)

    actual = fake_model_directive.run()

    for i, node in enumerate(expected):
        assert str(node) == str(actual[i])
