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
import typing
from typing import Annotated

import pydantic
import pytest
import yaml
from docutils import nodes
from docutils.core import publish_doctree
from pydantic_kitbash.directives import (
    build_examples_block,
    create_field_node,
    create_table_node,
    find_field_data,
    format_type_string,
    get_annotation_docstring,
    get_enum_member_docstring,
    get_enum_values,
    is_deprecated,
    is_enum_type,
    parse_rst_description,
    strip_whitespace,
)


class EnumType(enum.Enum):
    VALUE = "value"


def validator(value: str) -> str:
    return value.strip()


TEST_TYPE = Annotated[
    str,
    pydantic.AfterValidator(validator),
    pydantic.BeforeValidator(validator),
    pydantic.Field(
        description="This is the description of test type.",
        examples=["str1", "str2", "str3"],
    ),
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

    * - Values
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


# Test for `find_field_data`
def test_find_field_data():
    metadata = getattr(TEST_TYPE, "__metadata__", None)
    if metadata is not None:
        expected = metadata[2]
        actual = find_field_data(metadata)
        assert expected == actual
    else:
        pytest.fail("No metadata found")


# Test for `find_field_data` when none is present
def test_find_field_data_none():
    expected = None
    actual = find_field_data(getattr(TYPE_NO_FIELD, "__metadata__", None))

    assert expected == actual


# Test for `is_deprecated`
def test_is_deprecated():
    class Model(pydantic.BaseModel):
        field1: TEST_TYPE
        field2: str = pydantic.Field(deprecated=False)
        field3: str = pydantic.Field(deprecated=True)
        union_field: str | None = pydantic.Field(
            deprecated="pls don't use this :)",
        )

    assert not is_deprecated(Model, "field1")
    assert not is_deprecated(Model, "field2")
    assert is_deprecated(Model, "field3") == "This key is deprecated."
    assert is_deprecated(Model, "union_field") == "Deprecated. pls don't use this :)"


# Test for `is_deprecated` when passed an invalid field
def test_is_deprecated_invalid():
    class Model(pydantic.BaseModel):
        field1: TEST_TYPE

    try:
        is_deprecated(Model, "nope")
        pytest.fail("Invalid fields should raise a ValueError.")
    except ValueError:
        assert True


# Test for `is_enum_type`
def test_is_enum_type():
    class Model(pydantic.BaseModel):
        field: EnumType

    assert is_enum_type(Model.model_fields["field"].annotation)


# Test for `is_enum_type` when false
def test_is_enum_type_false():
    class Model(pydantic.BaseModel):
        field: int

    assert not is_enum_type(Model.model_fields["field"].annotation)


# Test for `create_field_node`
def test_create_field_node():
    # need to set up section node manually
    expected = nodes.section(ids=["key-name"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="key-name")
    expected += title_node
    expected += publish_doctree(KEY_ENTRY_RST).children

    # "Values" and "Examples" are tested separately because while
    # their HTML output is identical, their docutils are structured
    # differently from the publich_doctree output
    actual = create_field_node(
        "key-name", "Don't use this.", "str", "This is the key description", None, None
    )

    assert str(expected) == str(actual)


# Test for `build_examples_block` with valid input
def test_build_valid_examples_block():
    # Not using publish_doctree because the nodes differ, despite the HTML
    # of the rendered output being identical. This test could be improved
    # by using publish_doctree and the Sphinx HTML writer, which I couldn't
    # seem to get working.
    yaml_str = "test: {subkey: [good, nice]}"
    yaml_str = yaml.dump(yaml.safe_load(yaml_str), default_flow_style=False)
    yaml_str = yaml_str.replace("- ", "  - ").rstrip("\n")

    expected = nodes.literal_block(text=yaml_str)
    expected["language"] = "yaml"

    actual = build_examples_block("test", "subkey: [good, nice]")

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


# Test for `build_examples_block` with invalid input
@pytest.mark.filterwarnings("ignore::UserWarning")
def test_build_invalid_examples_block():
    yaml_str = "{[ oops"

    expected = nodes.literal_block(text=yaml_str)
    expected["language"] = "yaml"

    actual = build_examples_block("", yaml_str)

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


# Test for `create_table_node`
def test_create_table_node():
    expected = nodes.container()
    expected += publish_doctree(TABLE_RST).children

    actual = create_table_node([["1.1", "1.2"], ["2.1", "2.2"]])

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


# Test for `get_annotation_docstring`
def test_get_annotation_docstring():
    class MockModel(pydantic.BaseModel):
        field1: int

        field2: str
        """The second field."""

        """Should never see this docstring."""

    assert get_annotation_docstring(MockModel, "field1") is None
    assert get_annotation_docstring(MockModel, "field2") == "The second field."


# Test for `get_enum_member_docstring`
def test_get_enum_member_docstring():
    class MockEnum(enum.Enum):
        VAL1 = "one"

        VAL2 = "two"
        """This is the second value."""

        """Should never see this docstring."""

    assert get_enum_member_docstring(MockEnum, "VAL1") is None
    assert get_enum_member_docstring(MockEnum, "VAL2") == "This is the second value."


# Test for `get_enum_values`
def test_get_enum_values():
    class MockEnum(enum.Enum):
        VAL1 = "one"
        """Docstring 1."""

        VAL2 = "two"
        """Docstring 2."""

    assert get_enum_values(MockEnum) == [
        ["one", "Docstring 1."],
        ["two", "Docstring 2."],
    ]


# Test for `parse_rst_description`
def test_parse_rst_description():
    # use docutils to build rST like Sphinx would
    expected = publish_doctree(RST_SAMPLE).children
    # function output
    actual = parse_rst_description(RST_SAMPLE)

    # comparing strings because docutils `__eq__`
    # method compares by identity rather than state
    assert str(expected) == str(actual)


# Test for `strip_whitespace`
def test_strip_whitespace():
    docstring1 = """Description.

      **Examples**

      .. code-block:: yaml

          test: passed

      """

    docstring2 = """\
      Description.

      **Examples**

      .. code-block:: yaml

          test: passed

      """

    expected = (
        "Description.\n\n**Examples**\n\n.. code-block:: yaml\n\n    test: passed\n"
    )

    assert strip_whitespace(docstring1) == expected
    assert strip_whitespace(docstring2) == expected
    assert strip_whitespace(None) == ""


# Test for `format_type_string`
def test_format_type_string():
    type1 = typing.Annotated[str, pydantic.Field(description="test")]

    test_list = typing.Literal["val1", "val2", "val3"]

    assert format_type_string(getattr(type1, "__origin__", None)) == "str"
    assert format_type_string(test_list) == "Any of: ['val1', 'val2', 'val3']"
