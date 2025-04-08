import enum
import pydantic
import pytest
import typing
import yaml

from docutils import nodes
from docutils.core import publish_doctree
from typing import Annotated

from pydantic_kitbash.directives import (
    find_field_data,
    is_deprecated,
    create_key_node,
    build_examples_block,
    create_table_node,
    create_table_row,
    get_annotation_docstring,
    get_enum_member_docstring,
    get_enum_values,
    parse_rst_description,
    strip_whitespace,
    format_type_string,
)


def validator(cls, value: str) -> str:
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

str

**Description**

This is the key description

"""

# Test for `find_field_data`


def test_find_field_data():
    expected = TEST_TYPE.__metadata__[2]
    actual = find_field_data(TEST_TYPE.__metadata__)

    assert expected == actual


# Test for `is_deprecated`
def test_is_deprecated():

    class Model(pydantic.BaseModel):
        field1: TEST_TYPE
        field2: str = pydantic.Field(
            deprecated=False
        )
        field3: str = pydantic.Field(
            deprecated=True
        )
        union_field: str | None = pydantic.Field(
            deprecated="pls don't use this :)",
        )

    assert not is_deprecated(Model, "field1")
    assert not is_deprecated(Model, "field2")
    assert is_deprecated(Model, "field3") == "This key is deprecated."
    assert is_deprecated(Model, "union_field") == "Deprecated. pls don't use this :)"


# Test for `create_key_node`
def test_create_key_node():
    expected = nodes.section(ids=["key-name"])
    title_node = nodes.title()
    title_node += nodes.literal(text="key-name")
    expected += title_node
    expected += publish_doctree(KEY_ENTRY_RST).children

    # "Values" and "Examples" are tested below
    actual = create_key_node("key-name",
                             "Don't use this.",
                             "str",
                             "This is the key description",
                             None,
                             None)

    print(f'\n{expected}\n\n{actual}\n')

    assert str(expected) == str(actual)


# Test for `build_examples_block`
def test_build_examples_block():
    yaml_str = "test: passed"

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

    assert str(expected) == str(actual)


# Test for `get_annotation_docstring`
def test_get_annotation_docstring():

    class MockModel(pydantic.BaseModel):
        field1: int

        field2: str
        """The second field."""

        """Should never see this docstring."""

    assert get_annotation_docstring(MockModel, "field1") == None
    assert get_annotation_docstring(MockModel, "field2") == "The second field."


# Test for `get_enum_member_docstring`
def test_get_enum_member_docstring():

    class MockEnum(enum.Enum):
        VAL1 = "one"

        VAL2 = "two"
        """This is the second value."""

        """Should never see this docstring."""

    assert get_enum_member_docstring(MockEnum, "VAL1") == None
    assert get_enum_member_docstring(
        MockEnum, "VAL2") == "This is the second value."


# Test for `get_enum_values`
def test_get_enum_values():

    class MockEnum(enum.Enum):
        VAL1 = "one"
        """Docstring 1."""

        VAL2 = "two"
        """Docstring 2."""

    assert get_enum_values(MockEnum) == [
        ["one", "Docstring 1."], ["two", "Docstring 2."]]


# Test for `parse_rst_description`
def test_parse_rst_description():
    # use docutils to build rST like Sphinx would
    expected = publish_doctree(RST_SAMPLE).children
    # function output
    actual = parse_rst_description(RST_SAMPLE)

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

    expected = "Description.\n\n**Examples**\n\n.. code-block:: yaml\n\n    test: passed\n"

    assert strip_whitespace(docstring1) == expected
    assert strip_whitespace(docstring2) == expected
    assert strip_whitespace(None) == ""


# Test for `format_type_string`
def test_format_type_string():
    type1 = typing.Annotated[str, pydantic.Field(description="test")]

    test_list = typing.Literal["val1", "val2", "val3"]
    type2 = test_list

    assert format_type_string(type1.__origin__) == "str"
    assert format_type_string(type2) == "Any of: ['val1', 'val2', 'val3']"
