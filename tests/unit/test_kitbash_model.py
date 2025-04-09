import enum
import pydantic
import pytest

from docutils import nodes
from docutils.core import publish_doctree
from docutils.parsers.rst.states import Body, NestedStateMachine
from pydantic_kitbash.directives import KitbashModelDirective, strip_whitespace
from sphinx.util.docutils import LoggingReporter
from typing import Annotated


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


def validator(cls, value: str) -> str:
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
    uniontype_field: str | None = pydantic.Field(
        description="This is types.UnionType",
    )
    enum_field: MockEnum
    enum_uniontype: MockEnum | None
    typing_union: TEST_TYPE | None


class OopsNoModel():
    field1: int


def test_kitbash_model_invalid():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".OopsNoModel"]
        options = {}
        content = []

    assert KitbashModelDirective.run(DirectiveState) == []


def test_kitbash_model():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".MockModel"]
        options = {}
        content = []

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

    actual = KitbashModelDirective.run(DirectiveState)

    assert str(expected) == str(actual)


def test_kitbash_model_content():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".MockModel"]
        options = {}
        content = ["``Test content``"]

    expected = []

    rendered_content = publish_doctree("``Test content``").children
    for node in rendered_content:
        expected.append(node)

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

    actual = KitbashModelDirective.run(DirectiveState)

    assert str(expected) == str(actual)


def test_kitbash_model_include_deprecated():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".MockModel"]
        options = {
            "include-deprecated": "mock_field",
        }
        content = []

    expected = []

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

    actual = KitbashModelDirective.run(DirectiveState)

    assert str(expected) == str(actual)


def test_kitbash_model_prepend_name():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".MockModel"]
        options = {
            "prepend-name": "prefix",
        }
        content = []

    expected = []

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

    actual = KitbashModelDirective.run(DirectiveState)

    assert str(expected) == str(actual)


def test_kitbash_model_append_name():

    class DirectiveState():
        name = "kitbash-model"
        arguments = [__module__ + ".MockModel"]
        options = {
            "append-name": "suffix",
        }
        content = []

    expected = []

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

    actual = KitbashModelDirective.run(DirectiveState)

    assert str(expected) == str(actual)