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
import types
import typing
import warnings

import pydantic
import yaml
from docutils import nodes
from docutils.core import publish_doctree  # type: ignore[reportUnknownVariableType]
from pydantic.fields import FieldInfo
from sphinx.util.docutils import SphinxDirective


class KitbashFieldDirective(SphinxDirective):
    """Define the kitbash-field directive's data and behavior."""

    required_arguments = 2
    has_content = False
    final_argument_whitespace = True

    option_spec = {
        "skip-examples": bool,
        "skip-type": bool,
        "override-name": str,
        "prepend-name": str,
        "append-name": str,
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

        field_name = self.arguments[1]

        # grab pydantic field data
        field_params = pydantic_class.model_fields[field_name]

        field_alias = field_params.alias if field_params.alias else field_name

        description_str = get_annotation_docstring(pydantic_class, field_name)
        # Use JSON description value if docstring doesn't exist
        description_str = (
            field_params.description if description_str is None else description_str
        )

        examples = field_params.examples
        enum_values = None

        # if field is optional "normal" type (e.g., str | None)
        if isinstance(field_params.annotation, types.UnionType):
            union_args = typing.get_args(field_params.annotation)
            field_type: str | None = format_type_string(union_args[0])
            if issubclass(union_args[0], enum.Enum):
                description_str = (
                    union_args[0].__doc__
                    if description_str is None
                    else description_str
                )
                enum_values = get_enum_values(union_args[0])
        else:
            field_type = format_type_string(field_params.annotation)

        # if field is optional annotated type (e.g., VersionStr | None)
        if typing.get_origin(field_params.annotation) is typing.Union:
            annotated_type = field_params.annotation.__args__[0]
            # weird case: optional literal list fields
            if typing.get_origin(annotated_type) != typing.Literal:
                field_type = format_type_string(annotated_type.__args__[0])
            metadata = getattr(annotated_type, "__metadata__", None)
            field_annotation = find_field_data(metadata)
            if field_annotation and description_str is None and examples is None:
                description_str = field_annotation.description
                examples = field_annotation.examples
        elif isinstance(field_params.annotation, type):
            if issubclass(field_params.annotation, enum.Enum):
                # Use enum class docstring if field has no docstring
                description_str = (
                    field_params.annotation.__doc__
                    if description_str is None
                    else description_str
                )
                enum_values = get_enum_values(field_params.annotation)

        deprecation_warning = is_deprecated(pydantic_class, field_name)

        # Remove type if :skip-type: directive option was used
        field_type = None if "skip-type" in self.options else field_type

        # Remove examples if :skip-examples: directive option was used
        examples = None if "skip-examples" in self.options else examples

        field_alias = self.options.get("override-name", field_alias)

        # Get strings to concatenate with `field_alias`
        name_prefix = self.options.get("prepend-name", "")
        name_suffix = self.options.get("append-name", "")

        # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
        field_alias = f"{name_prefix}.{field_alias}" if name_prefix else field_alias
        field_alias = f"{field_alias}.{name_suffix}" if name_suffix else field_alias

        return [
            create_field_node(
                field_alias,
                deprecation_warning,
                field_type,
                description_str,
                enum_values,
                examples,
            )
        ]


class KitbashModelDirective(SphinxDirective):
    """Define the kitbash-model directive's data and behavior."""

    required_arguments = 1
    has_content = True
    final_argument_whitespace = True

    option_spec = {
        "include-deprecated": str,
        "prepend-name": str,
        "append-name": str,
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
        elif pydantic_class.__doc__:
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

                field_alias = field_params.alias if field_params.alias else field

                description_str = get_annotation_docstring(pydantic_class, field)
                # Use JSON description value if docstring doesn't exist
                description_str = (
                    field_params.description
                    if description_str is None
                    else description_str
                )

                examples = field_params.examples
                enum_values = None

                # if field is optional "normal" type (e.g., str | None)
                if (
                    field_params.annotation
                    and typing.get_origin(field_params.annotation) is types.UnionType
                ):
                    union_args = typing.get_args(field_params.annotation)
                    field_type = format_type_string(union_args[0])
                    if issubclass(union_args[0], enum.Enum):
                        description_str = (
                            union_args[0].__doc__
                            if description_str is None
                            else description_str
                        )
                        enum_values = get_enum_values(union_args[0])
                else:
                    field_type = format_type_string(field_params.annotation)

                # if field is optional annotated type (e.g., `VersionStr | None`)
                if (
                    field_params.annotation
                    and typing.get_origin(field_params.annotation) is typing.Union
                ):
                    annotated_type = field_params.annotation.__args__[0]
                    # weird case: optional literal list fields
                    if typing.get_origin(annotated_type) != typing.Literal:
                        field_type = format_type_string(annotated_type.__args__[0])
                    metadata = getattr(annotated_type, "__metadata__", None)
                    field_annotation = find_field_data(metadata)
                    if (
                        field_annotation
                        and description_str is None
                        and examples is None
                    ):
                        description_str = field_annotation.description
                        examples = field_annotation.examples
                elif is_enum_type(field_params.annotation):
                    description_str = (
                        field_params.annotation.__doc__
                        if description_str is None
                        else description_str
                    )
                    enum_values = (
                        get_enum_values(field_params.annotation)
                        if field_params.annotation
                        else None
                    )

                # Get strings to concatenate with `field_alias`
                name_prefix = self.options.get("prepend-name", "")
                name_suffix = self.options.get("append-name", "")

                # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
                field_alias = (
                    f"{name_prefix}.{field_alias}" if name_prefix else field_alias
                )
                field_alias = (
                    f"{field_alias}.{field_alias}" if name_suffix else field_alias
                )

                class_node.append(
                    create_field_node(
                        field_alias,
                        deprecation_warning,
                        field_type,
                        description_str,
                        enum_values,
                        examples,
                    )
                )

        return class_node


def find_field_data(
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
    if metadata:
        for element in metadata:
            if isinstance(element, FieldInfo):
                return element

    return None


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


def is_enum_type(annotation: typing.Any) -> bool:  # noqa: ANN401
    """Check whether a field's type annotation is an enum.

    Checks if the provided annotation is an object and if it is a subclass
    of enum.Enum.

    Args:
        annotation (type): The field's type annotation.

    Returns:
        bool: True if the annotation is an enum. Else, false.

    """
    return isinstance(annotation, type) and issubclass(annotation, enum.Enum)


def create_field_node(
    field_name: str,
    deprecated_message: str | None,
    field_type: str | None,
    field_desc: str | None,
    field_values: list[list[str]] | None,
    field_examples: list[str] | None,
) -> nodes.section:
    """Create a section node containing all of the information for a single field.

    Args:
        field_name (str): The name of the field.
        deprecated_message (str): The field's deprecation warning.
        field_type (str): The field's type.
        field_desc (str): The field's description.
        field_values (list[list[str]]): The field's values (if it is an enum).
        field_examples (list[str]): The field's JSON examples.

    Returns:
        nodes.section: A section containing well-formed output for each provided field attribute.

    """
    field_node = nodes.section(ids=[field_name])
    field_node["classes"] = ["kitbash-entry"]
    title_node = nodes.title(text=field_name)
    field_node += title_node

    if deprecated_message:
        deprecated_node = nodes.important()
        deprecated_node += parse_rst_description(deprecated_message)
        field_node += deprecated_node

    if field_type:
        type_header = nodes.paragraph()
        type_header += nodes.strong(text="Type")
        type_value = nodes.paragraph()
        type_value += nodes.literal(text=field_type)
        field_node += type_header
        field_node += type_value

    if field_desc:
        desc_header = nodes.paragraph()
        desc_header += nodes.strong(text="Description")
        field_node += desc_header
        field_node += parse_rst_description(field_desc)

    if field_values:
        values_header = nodes.paragraph()
        values_header += nodes.strong(text="Values")
        field_node += values_header
        field_node += create_table_node(field_values)

    if field_examples:
        examples_header = nodes.paragraph()
        examples_header += nodes.strong(text="Examples")
        field_node += examples_header
        for example in field_examples:
            field_node += build_examples_block(field_name, example)

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
    try:
        yaml_str = yaml.dump(yaml.safe_load(example), default_flow_style=False)
        yaml_str = yaml_str.rstrip("\n")
        yaml_str = yaml_str.replace("- ", "  - ").removesuffix("...")
        if len(yaml_str.splitlines()) == 1:
            yaml_str = f"{field_name.rsplit('.', maxsplit=1)[-1]}: {yaml_str}"
        else:
            yaml_str = textwrap.indent(yaml_str, "  ")
            yaml_str = f"{field_name.rsplit('.', maxsplit=1)[-1]}:\n{yaml_str}"
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
                docstring = typing.cast(ast.Constant, node.value).value
            break
        if (
            isinstance(node, ast.AnnAssign)
            and typing.cast(ast.Name, node.target).id == annotation_name
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
        node = typing.cast(ast.ClassDef, node)
        for i, inner_node in enumerate(node.body):
            if isinstance(inner_node, ast.Assign):
                for target in inner_node.targets:
                    if isinstance(target, ast.Name) and target.id == enum_member:
                        docstring_node = node.body[i + 1]
                        if isinstance(docstring_node, ast.Expr):
                            docstring_node_value = typing.cast(
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
    rst_doc = typing.cast(nodes.document, publish_doctree(strip_whitespace(rst_desc)))

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


def format_type_string(type_str: type[object] | typing.Any) -> str:  # noqa: ANN401
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

    pattern = r"Literal\[(.*?)\]"
    if match := re.search(pattern, str(type_str)):
        string_list = match.group(1)
        list_items = re.findall(r"'([^']*)'", string_list)
        result = f"Any of: {list_items}"
    elif type_str is not None:
        result = type_str.__name__

    return result
