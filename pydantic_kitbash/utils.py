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

"""Contains functions for pulling and formatting data from the target model."""

import ast
import importlib
import inspect
import re
import textwrap
from enum import Enum
from typing import Any, cast

from pydantic import AfterValidator, BaseModel, BeforeValidator
from pydantic.fields import FieldInfo

TYPE_STR_EXPR = re.compile(r"<[^ ]+ '([^']+)'>")
MODULE_PREFIX_EXPR = re.compile(r"\b(?:[A-Za-z_]\w*\.)+([A-Za-z_]\w*)")


def get_pydantic_model(
    py_module: str,
    model_name: str,
    field_name: str,
) -> type[BaseModel]:
    """Import the model specified by the given directive's arguments.

    Args:
        py_module (str): The python module declared by py:currentmodule
        model_name (str): The model name passed from the directive (<directive>.arguments[0])
        field_name (str): The field name passed from the directive (<directive.arguments[1])

    Returns:
        type[pydantic.BaseModel]

    """
    model_path = f"{py_module}.{model_name}" if py_module else model_name

    module_str, class_str = model_path.rsplit(".", maxsplit=1)
    try:
        module = importlib.import_module(module_str)
    except ModuleNotFoundError:
        raise ImportError(
            f"Module '{module_str}' does not exist or cannot be imported."
        )

    if not hasattr(module, class_str):
        raise AttributeError(f"Module '{module_str}' has no model '{class_str}'")

    pydantic_model = getattr(module, class_str)

    if not isinstance(pydantic_model, type) or not issubclass(
        pydantic_model, BaseModel
    ):
        raise TypeError(f"'{class_str}' is not a subclass of pydantic.BaseModel")

    if field_name:
        if field_name not in pydantic_model.model_fields:
            raise AttributeError(f"Could not find field '{field_name}'")

        for cls in pydantic_model.__mro__:
            if (
                issubclass(cls, BaseModel)
                and hasattr(cls, "__annotations__")
                and field_name in cls.__annotations__
            ):
                pydantic_model = cls
                break

    return pydantic_model


def find_fieldinfo(
    metadata: tuple[BeforeValidator, AfterValidator, FieldInfo] | None,
) -> FieldInfo | None:
    """Retrieve a field's information from its metadata.

    Iterate over an annotated type's metadata and return the first instance
    of a FieldInfo object. This is to account for fields having option
    before_validators and after_validators.

    Args:
        metadata (type[object] | None): Dictionary containing the field's metadata.

    Returns:
        FieldInfo: The Pydantic field's attribute values (description, examples, etc.)

    """
    result = None

    if metadata:
        for element in metadata:
            if isinstance(element, FieldInfo):
                result = element
    else:
        result = None

    return result


def is_deprecated(model: type[BaseModel], field: str) -> str | None:
    """Retrieve a field's deprecation message if one exists.

    Check to see whether the field's deprecated parameter is truthy or falsy.
    If truthy, it will return the parameter's value with a standard "Deprecated."
    prefix.

    Args:
        model (type[object]): The model containing the field a user wishes to examine.
        field (str): The field that is checked for a deprecation value.

    Returns:
        str: Returns deprecation message if one exists. Else, returns None.

    """
    if field not in model.__annotations__:
        raise ValueError(f"Could not find field: {field}")

    field_params = model.model_fields[field]
    warning = getattr(field_params, "deprecated", None)

    if warning:
        if isinstance(warning, str):
            warning = f"Deprecated. {warning}"
        else:
            warning = "This key is deprecated."

    return warning


def get_enum_values(enum_class: type[object]) -> list[tuple[str, str]]:
    """Get enum values and docstrings.

    Traverses an enum class, returning a list of tuples, where each tuple
    contains the attribute value and its respective docstring.

    Args:
        enum_class: A python type.

    Returns:
        list[list[str]]: The enum's values and docstrings.

    """
    enum_docstrings: list[tuple[str, str]] = []

    for attr, attr_value in enum_class.__dict__.items():
        if not attr.startswith("_"):
            docstring = get_enum_member_docstring(enum_class, attr)
            if docstring:
                enum_docstrings.append((f"{attr_value.value}", f"{docstring}"))

    return enum_docstrings


def get_enum_member_docstring(cls: type[object], enum_member: str) -> str | None:
    """Traverse class and return enum member docstring.

    Traverses a class AST until it finds the provided enum attribute. If the enum
    is followed by a docstring, that docstring is returned to the calling function. Else,
    it returns none.

    Args:
        cls (type[object]): An enum class.
        enum_member (str): The specific enum member to retrieve the docstring from.

    Returns:
        str: The docstring directly beneath the provided enum member.

    """
    source = inspect.getsource(cls)
    tree = ast.parse(textwrap.dedent(source))

    for node in tree.body:
        node = cast(ast.ClassDef, node)
        for i, inner_node in enumerate(node.body):
            if isinstance(inner_node, ast.Assign):
                for target in inner_node.targets:
                    if isinstance(target, ast.Name) and target.id == enum_member:
                        docstring_node = node.body[i + 1]
                        if isinstance(docstring_node, ast.Expr):
                            docstring_node_value = cast(
                                ast.Constant, docstring_node.value
                            )
                            return str(docstring_node_value.value)

    return None


def is_enum_type(annotation: Any) -> bool:  # noqa: ANN401
    """Check whether a field's type annotation is an enum.

    Checks if the provided annotation is an object and if it is a subclass
    of enum.Enum.

    Args:
        annotation (type): The field's type annotation.

    Returns:
        bool: True if the annotation is an enum. Else, false.

    """
    return isinstance(annotation, type) and issubclass(annotation, Enum)


def get_annotation_docstring(cls: type[object], annotation_name: str) -> str | None:
    """Traverse class and return annotation docstring.

    Traverses a class AST until it finds the provided annotation attribute. If
    the annotation is followed by a docstring, that docstring is returned to the
    calling function. Else, it returns none.

    Args:
        cls (type[object]): A python class.
        annotation_name (str): The type annotation to check for a docstring.

    Returns:
        str: The docstring immediately beneath the provided type annotation.

    """
    source = inspect.getsource(cls)
    tree = ast.parse(textwrap.dedent(source))

    found = False
    docstring = None

    for node in ast.walk(tree):
        if found:
            if isinstance(node, ast.Expr):
                docstring = str(cast(ast.Constant, node.value).value)
            break
        if (
            isinstance(node, ast.AnnAssign)
            and cast(ast.Name, node.target).id == annotation_name
        ):
            found = True

    return docstring


def format_type_string(type_str: type[object] | Any) -> str:  # noqa: ANN401
    """Format a python type string.

    Accepts a type string and converts it it to a more user-friendly
    string to be displayed in the output.

    Input parameter is intentionally loosely typed, as the value
    is not important. The function only cares about the type itself.

    Args:
        type_str (type[object]): A Python type.

    Returns:
        str: A more human-friendly representation of the type.

    """
    result = ""

    if type_str is not None:
        result = re.sub(MODULE_PREFIX_EXPR, r"\1", str(type_str))
        if type_match := re.match(TYPE_STR_EXPR, str(type_str)):
            result = type_match.group(1).split(".")[-1]

    return result
