### TEMPORARY LOCAL COPY FOR INTEGRATION TESTING
### REMOVE ONCE PUBLISHED ON PYPI

import ast
import enum
import importlib
import inspect
import json
import re
import textwrap
import types
import typing
import warnings

import pydantic
import yaml
from docutils import nodes
from docutils.core import publish_doctree
from docutils.parsers.rst import Directive
from pydantic.fields import FieldInfo
from sphinx.application import Sphinx
from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata


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
        """Access the docstrings and data from a user-provided Pydantic field
        to produce a formatted output in accordance with Starcraft's YAML key
        documentation standard.

        Parameters
        ----------

        Returns
        -------

        """
        module_str, class_str = self.arguments[0].rsplit(".", maxsplit=1)
        module = importlib.import_module(module_str)
        pydantic_class = getattr(module, class_str)

        # exit if provided field name is not present in the model
        if self.arguments[1] not in pydantic_class.__annotations__:
            raise ValueError(f"Could not find field {self.arguments[1]}")

        field_name = self.arguments[1]

        # grab pydantic field data
        field_params = pydantic_class.model_fields[field_name]

        if field_params.alias:
            field_alias = field_params.alias
        else:
            field_alias = field_name

        description_str = get_annotation_docstring(pydantic_class, field_name)
        if description_str is None:
            description_str = field_params.description  # use JSON description value

        examples = field_params.examples
        enum_values = None

        # if field is optional "normal" type (e.g., str | None)
        if isinstance(field_params.annotation, types.UnionType):
            union_args = typing.get_args(field_params.annotation)
            field_type = format_type_string(union_args[0])
            if issubclass(union_args[0], enum.Enum):
                if description_str is None:
                    description_str = union_args[0].__doc__
                enum_values = get_enum_values(union_args[0])
        else:
            field_type = format_type_string(field_params.annotation)

        # if field is optional annotated type (e.g., VersionStr | None)
        if typing.get_origin(field_params.annotation) is typing.Union:
            annotated_type = field_params.annotation.__args__[0]
            # weird case: optional literal list fields
            if not isinstance(annotated_type, typing._LiteralGenericAlias):
                field_type = format_type_string(annotated_type.__args__[0])
            metadata = getattr(annotated_type, "__metadata__", None)
            field_annotation = find_field_data(metadata)
            if field_annotation:
                if description_str is None and examples is None:
                    description_str = field_annotation.description
                    examples = field_annotation.examples
        elif isinstance(field_params.annotation, type):
            if issubclass(field_params.annotation, enum.Enum):
                if description_str is None:
                    # Use enum class docstring if field has no docstring
                    description_str = field_params.annotation.__doc__
                enum_values = get_enum_values(field_params.annotation)

        deprecation_warning = is_deprecated(pydantic_class, field_name)

        # Remove type if :skip-type: directive option was used
        if "skip-type" in self.options:
            field_type = None

        # Remove examples if :skip-examples: directive option was used
        if "skip-examples" in self.options:
            examples = None

        field_alias = self.options.get("override-name", field_alias)

        # Get strings to concatenate with `field_alias`
        name_prefix = self.options.get("prepend-name", "")
        name_suffix = self.options.get("append-name", "")

        # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
        if name_prefix:
            field_alias = f"{name_prefix}.{field_alias}"
        if name_suffix:
            field_alias = f"{field_alias}.{name_suffix}"

        return [create_key_node(field_alias, deprecation_warning, field_type, description_str, enum_values, examples)]


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

        Parameters
        ----------

        Returns
        -------

        """
        module_str, class_str = self.arguments[0].rsplit(".", maxsplit=1)
        module = importlib.import_module(module_str)
        pydantic_class = getattr(module, class_str)

        if not issubclass(pydantic_class, pydantic.BaseModel):
            return []

        class_node = []

        # User-provided description overrides model docstring
        if self.content:
            class_node += parse_rst_description("\n".join(self.content))
        else:
            class_node += parse_rst_description(pydantic_class.__doc__)

        # Check if user provided a list of deprecated fields to include
        deprecated_option = self.options.get("include-deprecated", "")
        include_deprecated = [field.strip()
                              for field in deprecated_option.split(",")]

        for field in pydantic_class.__annotations__:
            is_auto_generated = field.startswith("_") or field.startswith("model_")

            if not is_auto_generated:
                deprecation_warning = is_deprecated(pydantic_class, field)

            if not is_auto_generated and deprecation_warning is None or field in include_deprecated:
                # grab pydantic field data (need desc and examples)
                field_params = pydantic_class.model_fields[field]

                if field_params.alias:
                    field_alias = field_params.alias
                else:
                    field_alias = field

                description_str = get_annotation_docstring(
                    pydantic_class, field)
                if description_str is None:
                    description_str = field_params.description  # use JSON description value

                examples = field_params.examples
                enum_values = None

                # if field is optional "normal" type (e.g., str | None)
                if isinstance(field_params.annotation, types.UnionType):
                    union_args = typing.get_args(field_params.annotation)
                    field_type = format_type_string(union_args[0])
                    if issubclass(union_args[0], enum.Enum):
                        if description_str is None:
                            description_str = union_args[0].__doc__
                        enum_values = get_enum_values(union_args[0])
                else:
                    field_type = format_type_string(field_params.annotation)

                # if field is optional annotated type (e.g., `VersionStr | None`)
                if typing.get_origin(field_params.annotation) is typing.Union:
                    annotated_type = field_params.annotation.__args__[0]
                    # weird case: optional literal list fields
                    if not isinstance(annotated_type, typing._LiteralGenericAlias):
                        field_type = format_type_string(annotated_type.__args__[0])
                    metadata = getattr(annotated_type, "__metadata__", None)
                    field_annotation = find_field_data(metadata)
                    if field_annotation:
                        if description_str is None and examples is None:
                            description_str = field_annotation.description
                            examples = field_annotation.examples
                elif isinstance(field_params.annotation, type):
                    if issubclass(field_params.annotation, enum.Enum):
                        if description_str is None:
                            description_str = field_params.annotation.__doc__
                        enum_values = get_enum_values(field_params.annotation)

                # Get strings to concatenate with `field_alias`
                name_prefix = self.options.get("prepend-name", "")
                name_suffix = self.options.get("append-name", "")

                # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
                if name_prefix:
                    field_alias = f"{name_prefix}.{field_alias}"
                if name_suffix:
                    field_alias = f"{field_alias}.{field_alias}"

                class_node.append(create_key_node(
                    field_alias, deprecation_warning, field_type, description_str, enum_values, examples))

        return class_node


def find_field_data(metadata: dict[str, typing.Any]) -> FieldInfo:
    """Iterate over an annotated type's metadata and return the first instance
    of a FieldInfo object. This is to account for fields having option
    before_validators and after_validators.

    Parameters
    ----------

    Returns
    -------

    """
    if metadata:
        for element in metadata:
            if isinstance(element, FieldInfo):
                return element

    return None


def is_deprecated(model: typing.Type[object], field: str) -> str:
    """Check to see whether the field's deprecated parameter is truthy or falsy.
    If truthy, it will return the parameter's value with a standard "Deprecated."
    prefix.

    Parameters
    ----------

    Returns
    -------

    """
    field_params = model.model_fields[field]
    warning = getattr(field_params, "deprecated", None)

    if warning:
        if isinstance(warning, str):
            warning = f"Deprecated. {warning}"
        else:
            warning = "This key is deprecated."

    return warning


def create_key_node(key_name: str, deprecated_message: str, key_type: str, key_desc: str, key_values: list[list[str]], key_examples: list[str]) -> nodes.section:
    """Create a section node containing all of the information for a single key.

    Parameters
    ----------

    Returns
    -------

    """
    key_node = nodes.section(ids=[key_name])
    key_node["classes"] = ["kitbash-entry"]
    title_node = nodes.title(text=key_name)
    key_node += title_node

    if deprecated_message:
        deprecated_node = nodes.important()
        # deprecated_node["classes"] = "important"
        # deprecated_node += nodes.title(text="Important")
        deprecated_node += parse_rst_description(deprecated_message)
        key_node += deprecated_node

    if key_type:
        type_header = nodes.paragraph()
        type_header += nodes.strong(text="Type")
        type_value = nodes.paragraph()
        type_value += nodes.literal(text=key_type)
        key_node += type_header
        key_node += type_value

    if key_desc:
        desc_header = nodes.paragraph()
        desc_header += nodes.strong(text="Description")
        key_node += desc_header
        key_node += parse_rst_description(key_desc)

    if key_values:
        values_header = nodes.paragraph()
        values_header += nodes.strong(text="Values")
        key_node += values_header
        key_node += create_table_node(key_values)

    if key_examples:
        examples_header = nodes.paragraph()
        examples_header += nodes.strong(text="Examples")
        key_node += examples_header
        for example in key_examples:
            key_node += build_examples_block(key_name, example)

    return key_node


def build_examples_block(key_name: str, example: str) -> nodes.literal_block:
    """Create code example with docutils literal_block.

    Creates a literal_block node before populating it with a properly formatted
    YAML string. Outputs warnings whenever invalid YAML is passed.

    Parameters
    ----------
        key_name (str):
        example (str):

    Returns
    -------

    """

    try:
        yaml_str = yaml.dump(yaml.safe_load(example), default_flow_style=False)
        yaml_str = yaml_str.replace("- ", "  - ").rstrip("\n")
        # yaml_str = textwrap.indent(yaml_string, "  ")
    except yaml.YAMLError as e:
        warnings.warn(f"Invalid YAML for key {key_name}: {e}", category=UserWarning)
        yaml_str = example

    # f'{key_name.rsplit(".", maxsplit=1)[-1]}: \n'
    examples_block = nodes.literal_block(text=yaml_str)
    examples_block["language"] = "yaml"

    return examples_block


def create_table_node(values: list[list[str]]) -> nodes.container:
    """Create docutils table node.

    Creates a container node containing a properly formatted table node.

    Parameters
    ----------

    Returns
    -------

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

    Parameters
    ----------

    Returns
    -------

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


# this is kinda gross
def get_annotation_docstring(cls: typing.Type[object], annotation_name: str) -> str:
    """Traverse class and return annotation docstring.

    Traverses a class AST until it finds the provided annotation attribute. If
    the annotation is followed by a docstring, that docstring is returned to the
    calling function. Else, it returns none.

    Parameters
    ----------

    Returns
    -------

    """
    source = inspect.getsource(cls)
    tree = ast.parse(textwrap.dedent(source))

    found = False
    docstring = None

    for node in ast.walk(tree):
        if found:
            if isinstance(node, ast.Expr):
                docstring = node.value.value
            break
        if isinstance(node, ast.AnnAssign) and node.target.id == annotation_name:
            found = True

    return docstring


# also kinda gross
def get_enum_member_docstring(cls: typing.Type[object], enum_member: str) -> str:
    """Traverse class and return enum member docstring.

    Traverses a class AST until it finds the provided enum attribute. If the enum
    is followed by a docstring, that docstring is returned to the calling function. Else,
    it returns none.

    Parameters
    ----------

    Returns
    -------

    """
    source = inspect.getsource(cls)
    tree = ast.parse(textwrap.dedent(source))

    for node in tree.body:
        for i, inner_node in enumerate(node.body):
            if isinstance(inner_node, ast.Assign):
                for target in inner_node.targets:
                    if isinstance(target, ast.Name) and target.id == enum_member:
                        docstring_node = node.body[i + 1]
                        if isinstance(node.body[i + 1], ast.Expr):
                            return docstring_node.value.value

    return None


def get_enum_values(enum_class: typing.Type[object]) -> list[list[str]]:
    """Get enum values and docstrings.

    Traverses an enum class, returning a list of tuples, where each tuple
    contains the attribute value and its respective docstring.

    Parameters
    ----------

    Returns
    -------

    """
    enum_docstrings = []

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

    Parameters
    ----------
        rst_desc (str): string containing reStructuredText

    Returns
    -------
        list[Node]: the docutils nodes produced by the rST

    """
    desc_nodes = []
    rst_doc = publish_doctree(strip_whitespace(rst_desc))
    for node in rst_doc.children:
        desc_nodes.append(node)

    return desc_nodes


def strip_whitespace(rst_desc: str) -> str:
    """Strip whitespace from multiline docstrings.

    Dedents whitespace from docstrings so that it can be successfully
    parsed as reStructuredText.

    Parameters
    ----------
      rst_desc (str): unformatted Python docstring

    Returns
    -------
      str: dedented string that can be parsed as rST

    """

    if rst_desc:
        # This is used instead of textwrap.dedent() to account for
        # docstrings starting with the line continuation character.
        lines = rst_desc.splitlines()
        first_line = lines[0]
        remaining_lines = lines[1:]

        dedented_remaining_lines = textwrap.dedent(
            "\n".join(remaining_lines)).splitlines()

        return "\n".join([first_line.strip(), *dedented_remaining_lines])

    return ""


def format_type_string(type_str: typing.Any) -> str:
    """Format a python type string.

    Accepts a type string and converts it it to a more user-friendly
    string to be displayed in the output.

    Parameters
    ----------
      type_str (typing.Any): a Python type

    Returns
    -------
      str: human-friendly type string

    """
    pattern = r"Literal\[(.*?)\]"

    if re.search(pattern, str(type_str)):
        string_list = re.search(pattern, str(type_str)).group(1)
        list_items = re.findall(r"'([^']*)'", string_list)
        return f"Any of: {list_items}"

    return type_str.__name__


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the sphinx extension.

    Parameters
    ----------
      app (Sphinx): Sphinx application

    Returns
    -------
      ExtensionMetadata: xtension metadata

    """
    app.add_directive("kitbash-field", KitbashFieldDirective)
    app.add_directive("kitbash-model", KitbashModelDirective)

    return {
        "version": "0.1",
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
