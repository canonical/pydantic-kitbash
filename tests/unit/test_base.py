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
# this program. If not, see <http://www.gnu.org/licenses/>.

import enum
from typing import Annotated, TypeVar

import pydantic
import pytest
import yaml
from docutils import nodes
from docutils.core import publish_doctree


class EnumType(enum.Enum):
    VALUE = "value"


def validator(value: str) -> str:
    return value.strip()


# Used for testing `get_optional_annotated_field_data` edge case
T = TypeVar("T")

UniqueList = Annotated[
    list[T],
    pydantic.Field(json_schema_extra={"uniqueItems": True}),
]

TYPE_NO_FIELD = Annotated[
    str,
    pydantic.AfterValidator(validator),
    pydantic.BeforeValidator(validator),
]

ENUM_TYPE = Annotated[
    EnumType,
    pydantic.Field(description="Enum field."),
]

RST_SAMPLE = """This is an rST sample.

**Examples**

.. code-block:: yaml

    test: passed

"""

TABLE_RST = """\

.. list-table::
    :header-rows: 1

    * - Value
      - Description
    * - ``1.1``
      - 1.2
    * - ``2.1``
      - 2.2

"""

KEY_ENTRY_RST = """\

.. important::

    Don't use this.

**Type**

``str``

**Description**

This is the key description

"""

LIST_YAML = """\
test:
  - item1: val1
    item2: val2
"""


LITERAL_LIST_ENTRY_RST = """\

.. important::

    Don't use this.

**Type**

One of: ``['one', 'two', 'three']``

**Description**

This is the key description

"""


def test_create_field_node(fake_field_directive):
    """Test for create_field_node."""

    # need to set up section node manually
    expected = nodes.section(ids=["key-name", "key-name"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="key-name")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "key-name"
    expected += target_node
    expected += publish_doctree(KEY_ENTRY_RST).children

    fake_field_directive.field_name = "key-name"
    fake_field_directive.field_alias = "key-name"
    fake_field_directive.label = "key-name"
    fake_field_directive.deprecation_warning = "Don't use this."
    fake_field_directive.field_type = "str"
    fake_field_directive.field_description = "This is the key description"

    # "Values" and "Examples" are tested separately because while
    # their HTML output is identical, their docutils nodes are structured
    # differently from the publish_doctree output
    actual = fake_field_directive._create_field_node()

    assert str(expected) == str(actual)


def test_create_field_node_literal_list(fake_field_directive):
    """Test for create_field_node with a FieldEntry of type Literal[]."""

    # need to set up section node manually
    expected = nodes.section(ids=["key-name", "key-name"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="key-name")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "key-name"
    expected += target_node
    expected += publish_doctree(LITERAL_LIST_ENTRY_RST).children

    fake_field_directive.field_name = "key-name"
    fake_field_directive.field_alias = "key-name"
    fake_field_directive.label = "key-name"
    fake_field_directive.deprecation_warning = "Don't use this."
    fake_field_directive.field_type = "Literal['one', 'two', 'three']"
    fake_field_directive.field_description = "This is the key description"
    actual = fake_field_directive._create_field_node()

    assert str(expected) == str(actual)


def test_create_minimal_field_node(fake_field_directive):
    """Test for create_field_node with a minimal set of attributes."""

    # need to set up section node manually
    expected = nodes.section(ids=["key-name", "key-name"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="key-name")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "key-name"
    expected += target_node

    fake_field_directive.field_name = "key-name"
    fake_field_directive.field_alias = "key-name"
    fake_field_directive.label = "key-name"

    actual = fake_field_directive._create_field_node()

    assert str(expected) == str(actual)


def test_build_valid_examples_block(fake_field_directive):
    """Test for _build_examples_block with valid input."""

    # Not using publish_doctree because the nodes differ, despite the HTML
    # of the rendered output being identical. This test could be improved
    # by using publish_doctree and the Sphinx HTML writer, which I couldn't
    # seem to get working.
    yaml_str = "test: {subkey: [good, nice]}"
    yaml_str = yaml.dump(yaml.safe_load(yaml_str), default_flow_style=False)
    yaml_str = yaml_str.replace("- ", "  - ").rstrip("\n")

    expected = nodes.literal_block(text=yaml_str)
    expected["language"] = "yaml"

    fake_field_directive.field_alias = "test"
    actual = fake_field_directive._build_examples_block("{subkey: [good, nice]}")

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


def test_build_list_example(fake_field_directive):
    """Test for build_examples_block when rendering lists of dicts."""
    expected = nodes.literal_block(text=(LIST_YAML.rstrip("\n")))
    expected["language"] = "yaml"

    fake_field_directive.field_alias = "test"
    actual = fake_field_directive._build_examples_block("[{item1: val1, item2: val2}]")

    assert str(expected) == str(actual)


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_build_invalid_examples_block(fake_field_directive):
    """Test for build_examples_block with invalid input."""

    expected = nodes.literal_block(text="test: {[ oops")
    expected["language"] = "yaml"

    fake_field_directive.field_alias = "test"
    actual = fake_field_directive._build_examples_block("{[ oops")

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


def test_create_table_node(fake_field_directive):
    """Test for create_table_node."""

    expected = nodes.container()
    expected += publish_doctree(TABLE_RST).children

    fake_field_directive.field_values = [["1.1", "1.2"], ["2.1", "2.2"]]
    actual = fake_field_directive._create_table_node()

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


def test_parse_rst_description(fake_field_directive):
    """Test parse_rst_description."""

    # use docutils to build rST like Sphinx would
    expected = publish_doctree(RST_SAMPLE).children
    # function output
    actual = fake_field_directive._parse_rst_description(RST_SAMPLE)

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


def test_get_optional_annotated_field_data_no_annotation(fake_field_directive):
    """\
    Test for get_optional_annotated_field_data when the first arg has no
    annotation.
    """

    class MockModel(pydantic.BaseModel):
        field1: str | UniqueList[str] = pydantic.Field(
            description="desc",
            examples=["one", "two"],
        )

    annotation = MockModel.model_fields["field1"].annotation
    fake_field_directive._get_optional_annotated_field_data(annotation)

    assert fake_field_directive.field_type is None
    assert fake_field_directive.field_description is None
    assert fake_field_directive.field_examples is None


def test_get_optional_annotated_field_data_none(fake_field_directive):
    """Test for get_optional_annotated_field_data when no field is provided."""

    assert fake_field_directive._get_optional_annotated_field_data(None) is None


def test_get_enum_field_data_none(fake_field_directive):
    """Test for get_enum_field_data when no annotation is provided."""

    assert fake_field_directive._get_enum_field_data(None) is None
