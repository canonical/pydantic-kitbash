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

import pytest
from docutils import nodes
from docutils.core import publish_doctree
from pydantic_kitbash.directives import strip_whitespace

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


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "i_dont_exist"}],
    indirect=True,
)
def test_kitbash_field_invalid(fake_field_directive):
    """Test for KitbashFieldDirective when passed a nonexistent field."""

    with pytest.raises(ValueError, match="Could not find field: i_dont_exist"):
        fake_field_directive.run()


def test_kitbash_field(fake_field_directive):
    """Test for KitbashFieldDirective."""

    expected = nodes.section(ids=["test", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

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
    "fake_field_directive",
    [{"arguments": ["MockFieldModel", "mock_field"]}],
    indirect=True,
)
def test_kitbash_field_py_module(fake_field_directive):
    """Test for KitbashFieldDirective."""
    fake_field_directive.env.ref_context["py:module"] = fake_field_directive.__module__

    expected = nodes.section(ids=["test", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

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
    "fake_field_directive", [{"content": ["*supplemental rST*"]}], indirect=True
)
def test_kitbash_field_content(fake_field_directive):
    """Test for KitbashFieldDirective when content is provided."""

    expected = nodes.section(ids=["test", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

    field_entry = """\

    .. important::

        Deprecated. ew.

    **Type**

    ``int``

    **Description**

    description

    *supplemental rST*

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive",
    [{"model_field": "no_desc", "content": ["*supplemental rST*"]}],
    indirect=True,
)
def test_kitbash_field_content_no_desc(fake_field_directive):
    """Test for KitbashFieldDirective when content is provided."""

    expected = nodes.section(ids=["no-desc", "docname-no-desc"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="no-desc")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-no-desc"
    expected += target_node

    field_entry = """\

    **Type**

    ``str``

    **Description**

    *supplemental rST*

    """

    field_entry = strip_whitespace(field_entry)
    expected += publish_doctree(field_entry).children
    actual = fake_field_directive.run()[0]

    assert str(expected) == str(actual)


@pytest.mark.parametrize(
    "fake_field_directive", [{"options": {"prepend-name": "prefix"}}], indirect=True
)
def test_kitbash_field_prepend_name(fake_field_directive):
    """Test for the -name options in KitbashFieldDirective."""

    expected = nodes.section(ids=["prefix.test", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="prefix.test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

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
    "fake_field_directive", [{"options": {"append-name": "suffix"}}], indirect=True
)
def test_kitbash_field_append_name(fake_field_directive):
    """Test for the -name options in KitbashFieldDirective."""

    expected = nodes.section(ids=["test.suffix", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test.suffix")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

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
def test_kitbash_field_override_type(fake_field_directive):
    """Test for the override-type option in KitbashFieldDirective."""

    expected = nodes.section(ids=["test", "docname-test"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-test"
    expected += target_node

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
    "fake_field_directive", [{"options": {"label": "custom-label"}}], indirect=True
)
def test_kitbash_field_label_option(fake_field_directive):
    """Test for the override-type option in KitbashFieldDirective."""

    expected = nodes.section(ids=["test", "custom-label"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="test")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "custom-label"
    expected += target_node

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
    "fake_field_directive",
    [{"model_field": "bad_example", "options": {"skip-examples": None}}],
    indirect=True,
)
def test_kitbash_field_skip_examples(fake_field_directive):
    """Test for the skip-examples option in KitbashFieldDirective."""

    expected = nodes.section(ids=["bad_example", "docname-bad_example"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="bad_example")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-bad_example"
    expected += target_node

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
def test_kitbash_field_enum(fake_field_directive):
    """Test for the KitbashFieldDirective when passed an enum field."""

    expected = nodes.section(ids=["enum_field", "docname-enum_field"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="enum_field")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-enum_field"
    expected += target_node

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
def test_kitbash_field_union_type(fake_field_directive):
    """Test for the KitbashFieldDirective when passed a types.UnionType field."""

    expected = nodes.section(ids=["uniontype_field", "docname-uniontype_field"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="uniontype_field")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-uniontype_field"
    expected += target_node

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
def test_kitbash_field_enum_union(fake_field_directive):
    """Test for the KitbashFieldDirective when passed an enum UnionType field."""

    expected = nodes.section(ids=["enum_uniontype", "docname-enum_uniontype"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="enum_uniontype")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-enum_uniontype"
    expected += target_node

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
def test_kitbash_field_typing_union(fake_field_directive):
    """Test for KitbashFieldDirective when passed a typing.Union field."""

    expected = nodes.section(ids=["typing_union", "docname-typing_union"])
    expected["classes"].append("kitbash-entry")
    title_node = nodes.title(text="typing_union")
    expected += title_node
    target_node = nodes.target()
    target_node["refid"] = "docname-typing_union"
    expected += target_node

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
