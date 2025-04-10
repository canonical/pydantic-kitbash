import enum
from typing import Annotated

import pydantic
import pytest
from docutils import nodes
from docutils.core import publish_doctree
from pydantic_kitbash.directives import KitbashFieldDirective, strip_whitespace

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


def test_kitbash_field_invalid():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "oops"]
        options = {}
        content = []

    try:
        KitbashFieldDirective.run(DirectiveState)[0]
        pytest.fail("Invalid fields should raise a ValueError.")
    except ValueError:
        assert True


def test_kitbash_field():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "mock_field"]
        options = {}
        content = []

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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_prepend_name():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "mock_field"]
        options = {"prepend-name": "app"}
        content = []

    expected = nodes.section(ids=["app.test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="app.test")
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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_append_name():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "mock_field"]
        options = {"append-name": "<part-name>"}
        content = []

    expected = nodes.section(ids=["test.<part-name>"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test.<part-name>")
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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_override_name():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "mock_field"]
        options = {"override-name": "override"}
        content = []

    expected = nodes.section(ids=["override"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="override")
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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_skip_type():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "mock_field"]
        options = {
            "skip-type": True,
        }
        content = []

    expected = nodes.section(ids=["test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node

    field_entry = """\

    .. important::

        Deprecated. ew.

    **Description**

    description

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_skip_examples():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "bad_example"]
        options = {
            "skip-examples": True,
        }
        content = []

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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_enum():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "enum_field"]
        options = {}
        content = []

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

    actual = KitbashFieldDirective.run(DirectiveState)[0]
    print(f"\n{expected}\n\n{actual}\n")
    assert str(expected) == str(actual)


def test_kitbash_field_union_type():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "uniontype_field"]
        options = {}
        content = []

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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_enum_union():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "enum_uniontype"]
        options = {}
        content = []

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

    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)


def test_kitbash_field_typing_union():
    class DirectiveState:
        name = "kitbash-field"
        arguments = [__module__ + ".MockModel", "typing_union"]
        options = {
            "skip-examples": True,
        }
        content = []

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
    actual = KitbashFieldDirective.run(DirectiveState)[0]

    assert str(expected) == str(actual)
