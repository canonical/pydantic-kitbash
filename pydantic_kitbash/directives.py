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

"""Define core functions of pydantic-kitbash directives.

Contains both of the pydantic-kitbash directives and their
supporting functions.
"""

import ast
import enum
import importlib
import inspect
import re
import textwrap
import warnings
from types import UnionType
from typing import Any, Literal, Union, cast, get_args, get_origin

import pydantic
import yaml
from docutils import nodes
from docutils.core import publish_doctree  # type: ignore[reportUnknownVariableType]
from docutils.parsers.rst import directives
from pydantic.fields import FieldInfo
from sphinx.util.docutils import SphinxDirective

# Compiled regex patterns for type formatting
LITERAL_LIST_EXPR = re.compile(r"Literal\[(.*?)\]")
LIST_ITEM_EXPR = re.compile(r"'([^']*)'")
TYPE_STR_EXPR = re.compile(r"<[^ ]+ '([^']+)'>")
MODULE_PREFIX_EXPR = re.compile(r"\b(?:\w+\.)+(\w+)")


class FieldEntry:
    """Contains any field attributes that will be displayed in directive output."""

    name: str
    alias: str
    deprecation_warning: str | None
    field_type: str | None
    description: str | None
    enum_values: list[list[str]] | None
    examples: list[str] | None

    def __init__(self, name: str) -> None:
        self.name = name
        self.alias = name
        self.deprecation_warning = None
        self.field_type = None
        self.description = None
        self.enum_values = None
        self.examples = None


class KitbashFieldDirective(SphinxDirective):
    """Define the kitbash-field directive's data and behavior."""

    required_arguments = 2
    has_content = False
    final_argument_whitespace = True

    option_spec = {
        "skip-examples": directives.flag,
        "override-type": directives.unchanged,
        "prepend-name": directives.unchanged,
        "append-name": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Generate an entry for the provided field.

        Access the docstring and data from a user-provided Pydantic field
        to produce a formatted output in accordance with Starcraft's YAML key
        documentation standard.

        Returns:
            list[nodes.Node]: Well-formed list of nodes to render into field entry.

        """
        module_str, class_str = self.arguments[0].rsplit(".", maxsplit=1)
        module = importlib.import_module(module_str)
        pydantic_class = getattr(module, class_str)

        # exit if provided field name is not present in the model
        if self.arguments[1] not in pydantic_class.__annotations__:
            raise ValueError(f"Could not find field: {self.arguments[1]}")

        field_entry = FieldEntry(self.arguments[1])

        # grab pydantic field data
        field_params = pydantic_class.model_fields[field_entry.name]

        field_entry.alias = (
            field_params.alias if field_params.alias else field_entry.name
        )

        field_entry.description = get_annotation_docstring(
            pydantic_class, field_entry.name
        )
        # Use JSON description value if docstring doesn't exist
        field_entry.description = (
            field_params.description
            if field_entry.description is None
            else field_entry.description
        )

        field_entry.examples = field_params.examples
        field_entry.enum_values = None

        # if field is optional "normal" type (e.g., str | None)
        if get_origin(field_params.annotation) is UnionType:
            get_optional_field_data(field_entry, field_params.annotation)
        else:
            field_entry.field_type = format_type_string(field_params.annotation)

        # if field is optional annotated type (e.g., VersionStr | None)
        if get_origin(field_params.annotation) is Union:
            get_optional_annotated_field_data(field_entry, field_params.annotation)
        elif is_enum_type(field_params.annotation):
            get_enum_field_data(field_entry, field_params.annotation)

        field_entry.deprecation_warning = is_deprecated(
            pydantic_class, field_entry.name
        )

        # Replace type if :override-type: directive option was used
        field_entry.field_type = self.options.get(
            "override-type", field_entry.field_type
        )

        # Remove examples if :skip-examples: directive option was used
        field_entry.examples = (
            None if "skip-examples" in self.options else field_entry.examples
        )

        # Get strings to concatenate with `field_alias`
        name_prefix = self.options.get("prepend-name", "")
        name_suffix = self.options.get("append-name", "")

        # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
        field_entry.alias = (
            f"{name_prefix}.{field_entry.alias}" if name_prefix else field_entry.alias
        )
        field_entry.alias = (
            f"{field_entry.alias}.{name_suffix}" if name_suffix else field_entry.alias
        )

        return [create_field_node(field_entry)]


class KitbashModelDirective(SphinxDirective):
    """Define the kitbash-model directive's data and behavior."""

    required_arguments = 1
    has_content = True
    final_argument_whitespace = True

    option_spec = {
        "include-deprecated": directives.unchanged,
        "skip-description": directives.flag,
        "prepend-name": directives.unchanged,
        "append-name": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Handle the core kitbash-model directive logic.

        Access every field in a user-provided Pydantic model
        to produce a formatted output in accordance with Starcraft's YAML key
        documentation standard.

        Args:
            self: Object containing the directive's state.

        Returns:
            list[nodes.Node]: Well-formed list of nodes to render into field entries.

        """
        module_str, class_str = self.arguments[0].rsplit(".", maxsplit=1)
        module = importlib.import_module(module_str)
        pydantic_class = getattr(module, class_str)

        if not issubclass(pydantic_class, pydantic.BaseModel):
            return []

        class_node: list[nodes.Node] = []

        # User-provided description overrides model docstring
        if self.content:
            class_node += parse_rst_description("\n".join(self.content))
        elif pydantic_class.__doc__ and "skip-description" not in self.options:
            class_node += parse_rst_description(pydantic_class.__doc__)

        # Check if user provided a list of deprecated fields to include
        include_deprecated = [
            field.strip()
            for field in self.options.get("include-deprecated", "").split(",")
        ]

        for field in pydantic_class.__annotations__:
            deprecation_warning = (
                is_deprecated(pydantic_class, field)
                if not field.startswith(("_", "model_"))
                else None
            )

            if (
                not field.startswith(("_", "model_"))
                and deprecation_warning is None
                or field in include_deprecated
            ):
                # grab pydantic field data (need desc and examples)
                field_params = pydantic_class.model_fields[field]

                field_entry = FieldEntry(field)
                field_entry.deprecation_warning = deprecation_warning

                field_entry.alias = (
                    field_params.alias if field_params.alias else field_entry.name
                )

                field_entry.description = get_annotation_docstring(
                    pydantic_class, field_entry.name
                )
                # Use JSON description value if docstring doesn't exist
                field_entry.description = (
                    field_params.description
                    if field_entry.description is None
                    else field_entry.description
                )

                field_entry.examples = field_params.examples
                field_entry.enum_values = None

                # if field is optional "normal" type (e.g., str | None)
                if (
                    field_params.annotation
                    and get_origin(field_params.annotation) is UnionType
                ):
                    get_optional_field_data(field_entry, field_params.annotation)
                else:
                    field_entry.field_type = format_type_string(field_params.annotation)

                # if field is optional annotated type (e.g., `VersionStr | None`)
                if (
                    field_params.annotation
                    and get_origin(field_params.annotation) is Union
                ):
                    get_optional_annotated_field_data(
                        field_entry, field_params.annotation
                    )
                elif is_enum_type(field_params.annotation):
                    get_enum_field_data(field_entry, field_params.annotation)

                # Get strings to concatenate with `field_alias`
                name_prefix = self.options.get("prepend-name", "")
                name_suffix = self.options.get("append-name", "")

                # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
                field_entry.alias = (
                    f"{name_prefix}.{field_entry.alias}"
                    if name_prefix
                    else field_entry.alias
                )
                field_entry.alias = (
                    f"{field_entry.alias}.{field_entry.alias}"
                    if name_suffix
                    else field_entry.alias
                )

                class_node.append(create_field_node(field_entry))

        return class_node


def get_optional_field_data(field_entry: FieldEntry, annotation: type[Any]) -> None:
    """Traverse the field and retrieve its type, description, and enum values.

    Args:
        field_entry (FieldEntry): Object containing field data.

        annotation (type[Any]): Type annotation of the optional field. This field
            may be either a standard Python type or an optional enum.

    Returns:
        None

    """
    union_args = get_args(annotation)
    field_entry.field_type = format_type_string(union_args[0])
    if issubclass(union_args[0], enum.Enum):
        field_entry.description = (
            union_args[0].__doc__
            if field_entry.description is None
            else field_entry.description
        )
        field_entry.enum_values = get_enum_values(union_args[0])


def get_optional_annotated_field_data(
    field_entry: FieldEntry, annotation: type[Any] | None
) -> None:
    """Traverse the field and retrieve its type, description, and examples.

    Args:
        field_entry (FieldEntry): Object containing field data.

        annotation (type[Any]): Annotation of an optional annotated type field.

    Returns:
        None

    """
    if annotation:
        annotated_type = annotation.__args__[0]
        # weird case: optional literal list fields
        if get_origin(annotated_type) != Literal and hasattr(
            annotated_type, "__args__"
        ):
            field_entry.field_type = format_type_string(annotated_type.__args__[0])
        metadata = getattr(annotated_type, "__metadata__", None)
        field_annotation = find_fieldinfo(metadata)
        if (
            field_annotation
            and field_entry.description is None
            and field_entry.examples is None
        ):
            field_entry.description = field_annotation.description
            field_entry.examples = field_annotation.examples


def get_enum_field_data(field_entry: FieldEntry, annotation: type[Any] | None) -> None:
    """Traverse the enum field and retrieve its docstring and enum values.

    Args:
        field_entry (FieldEntry): Object containing field data.

        annotation (type[Any]): Annotation for an enum field. This does not include
            optional enum fields, which are handled by `get_optional_field_data`.

    Returns:
        None

    """
    # Use enum class docstring if field has no docstring
    if annotation:
        field_entry.description = (
            annotation.__doc__
            if field_entry.description is None
            else field_entry.description
        )
        field_entry.enum_values = get_enum_values(annotation)


def find_fieldinfo(
    metadata: tuple[pydantic.BeforeValidator, pydantic.AfterValidator, FieldInfo]
    | None,
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


def is_deprecated(model: type[pydantic.BaseModel], field: str) -> str | None:
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


def is_enum_type(annotation: Any) -> bool:  # noqa: ANN401
    """Check whether a field's type annotation is an enum.

    Checks if the provided annotation is an object and if it is a subclass
    of enum.Enum.

    Args:
        annotation (type): The field's type annotation.

    Returns:
        bool: True if the annotation is an enum. Else, false.

    """
    return isinstance(annotation, type) and issubclass(annotation, enum.Enum)


def create_field_node(field_entry: FieldEntry) -> nodes.section:
    """Create a section node containing all of the information for a single field.

    Args:
        field_entry (FieldEntry): Object containing all of the field's data

    Returns:
        nodes.section: A section containing well-formed output for each provided field attribute.

    """
    field_node = nodes.section(ids=[field_entry.alias])
    field_node["classes"] = ["kitbash-entry"]
    title_node = nodes.title(text=field_entry.alias)
    field_node += title_node

    if field_entry.deprecation_warning:
        deprecated_node = nodes.important()
        deprecated_node += parse_rst_description(field_entry.deprecation_warning)
        field_node += deprecated_node

    if field_entry.field_type:
        type_header = nodes.paragraph()
        type_header += nodes.strong(text="Type")
        type_value = nodes.paragraph()
        type_value += nodes.literal(text=field_entry.field_type)
        field_node += type_header
        field_node += type_value

    if field_entry.description:
        desc_header = nodes.paragraph()
        desc_header += nodes.strong(text="Description")
        field_node += desc_header
        field_node += parse_rst_description(field_entry.description)

    if field_entry.enum_values:
        values_header = nodes.paragraph()
        values_header += nodes.strong(text="Values")
        field_node += values_header
        field_node += create_table_node(field_entry.enum_values)

    if field_entry.examples:
        examples_header = nodes.paragraph()
        examples_header += nodes.strong(text="Examples")
        field_node += examples_header
        for example in field_entry.examples:
            field_node += build_examples_block(field_entry.alias, example)

    return field_node


def build_examples_block(field_name: str, example: str) -> nodes.literal_block:
    """Create code example with docutils literal_block.

    Creates a literal_block node before populating it with a properly formatted
    YAML string. Outputs warnings whenever invalid YAML is passed.

    Args:
        field_name (str): The name of the field.
        example (str): The field example being formatted.

    Returns:
        nodes.literal_block: A literal block containing a well-formed YAML example.

    """
    example = f"{field_name.rsplit('.', maxsplit=1)[-1]}: {example}"
    try:
        yaml_str = yaml.dump(yaml.safe_load(example), default_flow_style=False)
        yaml_str = yaml_str.rstrip("\n")
        yaml_str = yaml_str.replace("- ", "  - ").removesuffix("...")
    except yaml.YAMLError as e:
        warnings.warn(
            f"Invalid YAML for field {field_name}: {e}",
            category=UserWarning,
            stacklevel=2,
        )
        yaml_str = example

    examples_block = nodes.literal_block(text=yaml_str)
    examples_block["language"] = "yaml"

    return examples_block


def create_table_node(values: list[list[str]]) -> nodes.container:
    """Create docutils table node.

    Creates a container node containing a properly formatted table node.

    Args:
        values (list[list[str]]): A list of value-description pairs.

    Returns:
        nodes.container: A `div` containing a well-formed docutils table.

    """
    div_node = nodes.container()
    table = nodes.table()
    div_node += table

    tgroup = nodes.tgroup(cols=2)
    table += tgroup

    tgroup += nodes.colspec(colwidth=50)
    tgroup += nodes.colspec(colwidth=50)

    thead = nodes.thead()
    header_row = nodes.row()

    values_entry = nodes.entry()
    values_entry += nodes.paragraph(text="Values")
    header_row += values_entry

    desc_entry = nodes.entry()
    desc_entry += nodes.paragraph(text="Description")
    header_row += desc_entry

    thead += header_row
    tgroup += thead

    tbody = nodes.tbody()
    tgroup += tbody

    for row in values:
        tbody += create_table_row(row)

    return div_node


def create_table_row(values: list[str]) -> nodes.row:
    """Create well-formed docutils table row.

    Creates a well-structured docutils table row from
    the strings provided in values.

    Args:
        values (list[str]): A list containing a value and description.

    Returns:
        nodes.row: A table row consisting of the provided value and description.

    """
    row = nodes.row()

    value_entry = nodes.entry()
    value_p = nodes.paragraph()
    value_p += nodes.literal(text=values[0])
    value_entry += value_p
    row += value_entry

    desc_entry = nodes.entry()
    desc_entry += parse_rst_description(values[1])
    row += desc_entry

    return row


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
                docstring = cast(ast.Constant, node.value).value
            break
        if (
            isinstance(node, ast.AnnAssign)
            and cast(ast.Name, node.target).id == annotation_name
        ):
            found = True

    return docstring


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


def get_enum_values(enum_class: type[object]) -> list[list[str]]:
    """Get enum values and docstrings.

    Traverses an enum class, returning a list of tuples, where each tuple
    contains the attribute value and its respective docstring.

    Args:
        enum_class: A python type.

    Returns:
        list[list[str]]: The enum's values and docstrings.

    """
    enum_docstrings: list[list[str]] = []

    for attr, attr_value in enum_class.__dict__.items():
        if not attr.startswith("_"):
            docstring = get_enum_member_docstring(enum_class, attr)
            if docstring:
                enum_docstrings.append([f"{attr_value.value}", f"{docstring}"])

    return enum_docstrings


def parse_rst_description(rst_desc: str) -> list[nodes.Node]:
    """Parse rST from model and field docstrings.

    Creates a reStructuredText document node from the given string so that
    the document's child nodes can be appended to the directive's output.

    Args:
        rst_desc (str): string containing reStructuredText

    Returns:
        list[Node]: the docutils nodes produced by the rST

    """
    rst_doc = cast(nodes.document, publish_doctree(strip_whitespace(rst_desc)))

    return list(rst_doc.children)


def strip_whitespace(rst_desc: str | None) -> str:
    """Strip whitespace from multiline docstrings.

    Dedents whitespace from docstrings so that it can be successfully
    parsed as reStructuredText.

    Args:
        rst_desc (str): An indented Python docstring.

    Returns:
        str: A properly dedented string that can be parsed as rST

    """
    if rst_desc:
        # This is used instead of textwrap.dedent() to account for
        # docstrings starting with the line continuation character.
        lines = rst_desc.splitlines()
        first_line = lines[0]
        remaining_lines = lines[1:]

        dedented_remaining_lines = textwrap.dedent(
            "\n".join(remaining_lines)
        ).splitlines()

        return "\n".join([first_line.strip(), *dedented_remaining_lines])

    return ""


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

    if match := re.search(LITERAL_LIST_EXPR, str(type_str)):
        string_list = match.group(1)
        list_items = re.findall(LIST_ITEM_EXPR, string_list)
        result = f"Any of: {list_items}"
    elif type_str is not None:
        result = re.sub(MODULE_PREFIX_EXPR, r"\1", str(type_str))
        if type_match := re.match(TYPE_STR_EXPR, str(type_str)):
            result = type_match.group(1).split(".")[-1]

    return result
