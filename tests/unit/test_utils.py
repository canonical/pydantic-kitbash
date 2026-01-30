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
import re
import typing
from importlib import import_module
from typing import Annotated

import pydantic
import pytest
from pydantic_kitbash.utils import (
    MODULE_PREFIX_EXPR,
    find_fieldinfo,
    format_type_string,
    get_annotation_docstring,
    get_enum_member_docstring,
    get_enum_values,
    get_pydantic_model,
    is_deprecated,
    is_enum_type,
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


class MockObject:
    # contents don't matter, this is just for testing type formatting
    the_real_treasure: str

    def __init__(self):
        self.the_real_treasure = "the friends we made along the way"


def test_get_pydantic_model():
    """Test for get_pydantic_model with valid input."""

    module = import_module("tests.unit.conftest")
    expected = module.MockModel
    actual = get_pydantic_model("", "tests.unit.conftest.MockModel", "")

    assert type(expected) is type(actual)


def test_get_pydantic_model_with_module():
    """Test for get_pydantic_model when py:module is set."""
    module = import_module("tests.unit.conftest")
    expected = module.MockModel

    actual = get_pydantic_model("tests.unit.conftest", "MockFieldModel", "mock_field")

    assert type(expected) is type(actual)


def test_get_pydantic_model_bad_import():
    """Test for get_pydantic_model when passes a nonexistent module."""

    with pytest.raises(
        ImportError,
        match="Module 'this.does.not.exist' does not exist or cannot be imported.",
    ):
        get_pydantic_model("this.does.not.exist", "", "")


def test_get_pydantic_model_nonexistent_model():
    """Test for get_pydantic_model when passes a nonexistent class."""

    with pytest.raises(
        AttributeError, match="Module 'tests.unit.conftest' has no model 'DoesNotExist'"
    ):
        get_pydantic_model("tests.unit.conftest", "DoesNotExist", "")


def test_get_pydantic_model_invalid_class():
    """Test for get_pydantic_model when passes a non-Model class."""

    with pytest.raises(
        TypeError, match="'OopsNoModel' is not a subclass of pydantic.BaseModel"
    ):
        get_pydantic_model("tests.unit.conftest", "OopsNoModel", "")


def test_find_fieldinfo():
    """Test for find_fieldinfo with valid input."""

    metadata = getattr(TEST_TYPE, "__metadata__", None)
    if metadata is not None:
        expected = metadata[2]
        actual = find_fieldinfo(metadata)
        assert expected == actual
    else:
        pytest.fail("No metadata found")


def test_find_fieldinfo_none():
    """Test for find_fieldinfo() when no FieldInfo object is present."""
    expected = None
    actual = find_fieldinfo(None)

    assert expected == actual


def test_is_deprecated():
    """Test for is_deprecated()"""

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


def test_is_deprecated_invalid():
    """Test for is_deprecated when passed a nonexistent field."""

    class Model(pydantic.BaseModel):
        field1: TEST_TYPE

    try:
        is_deprecated(Model, "nope")
        pytest.fail("Invalid fields should raise a ValueError.")
    except ValueError:
        assert True


def test_is_enum_type():
    """Test for is_enum_type when passed an enum."""

    class Model(pydantic.BaseModel):
        field: EnumType

    assert is_enum_type(Model.model_fields["field"].annotation)


def test_is_enum_type_false():
    """Test for is_enum_type when passed a non-enum field."""

    class Model(pydantic.BaseModel):
        field: int

    assert not is_enum_type(Model.model_fields["field"].annotation)


def test_get_annotation_docstring():
    """Test for get_annotation_docstring."""

    class MockModel(pydantic.BaseModel):
        field1: int

        field2: str
        """The second field."""

        """Should never see this docstring."""

    assert get_annotation_docstring(MockModel, "field1") is None
    assert get_annotation_docstring(MockModel, "field2") == "The second field."


def test_get_enum_member_docstring():
    """Test for get_enum_member_docstring."""

    class MockEnum(enum.Enum):
        VAL1 = "one"

        VAL2 = "two"
        """This is the second value."""

        """Should never see this docstring."""

    assert get_enum_member_docstring(MockEnum, "VAL1") is None
    assert get_enum_member_docstring(MockEnum, "VAL2") == "This is the second value."


def test_get_enum_values():
    """Test for get_enum_values."""

    class MockEnum(enum.Enum):
        VAL1 = "one"
        """Docstring 1."""

        VAL2 = "two"
        """Docstring 2."""

    assert get_enum_values(MockEnum) == [
        ("one", "Docstring 1."),
        ("two", "Docstring 2."),
    ]


@pytest.mark.parametrize(
    ("type_str"),
    [
        pytest.param("foo.bar"),
        pytest.param("Foo.Bar"),
        pytest.param("Foo1.bar"),
        pytest.param("_foo.bar"),
        pytest.param("foo.bar1"),
        pytest.param("foo._bar"),
    ],
)
def test_module_prefix_regex_match(type_str):
    """Test strings that match against the regex for Python module paths."""
    assert re.match(MODULE_PREFIX_EXPR, type_str)


@pytest.mark.parametrize(
    ("type_str"),
    [
        pytest.param("foo"),
        pytest.param("foo."),
        pytest.param(".foo"),
        pytest.param("1foo.bar"),
        pytest.param("foo.1bar"),
        pytest.param("foo@bar.baz"),
        pytest.param("foo-bar.foo-baz"),
    ],
)
def test_module_prefix_regex_no_match(type_str):
    """Test strings that don't match against the regex for Python module paths."""
    assert not re.match(MODULE_PREFIX_EXPR, type_str)


def test_format_type_string():
    """Test for format_type_string."""

    annotated_type = typing.Annotated[str, pydantic.Field(description="test")]
    object_type = type(MockObject())
    list_type = typing.Literal["val1", "val2", "val3"]

    assert format_type_string(None) == ""
    assert format_type_string(getattr(annotated_type, "__origin__", None)) == "str"
    assert format_type_string("dict[idk.man.str, typing.Any]") == "dict[str, Any]"
    assert format_type_string(object_type) == "MockObject"
    assert format_type_string(list_type) == "Literal['val1', 'val2', 'val3']"
    assert (
        format_type_string("typing.Literal['foo@1.0', 'foo@1.1']")
        == "Literal['foo@1.0', 'foo@1.1']"
    )
