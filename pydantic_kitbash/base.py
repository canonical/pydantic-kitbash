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

"""Contains behavior common to the extension's two directives."""

import enum
import inspect
import re
import warnings
from pathlib import Path
from typing import Any, Literal, cast, get_args, get_origin

import yaml
from docutils import nodes
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sphinx.util.docutils import SphinxDirective
from typing_extensions import override

from pydantic_kitbash.utils import find_fieldinfo, format_type_string, get_enum_values


@override
class PrettyListDumper(yaml.Dumper):
    """Custom YAML dumper for indenting lists."""

    @override
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, indentless=False)


def str_presenter(dumper: yaml.Dumper, data: str) -> yaml.nodes.ScalarNode:
    """Use the "|" style when presenting multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")  # type: ignore[reportUnknownMemberType]
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)  # type: ignore[reportUnknownMemberType]


class KitbashDirective(SphinxDirective):
    """Contains any field attributes that will be displayed in directive output."""

    field_name: str
    field_alias: str
    label: str
    deprecation_warning: str | None
    field_type: str | None
    field_description: str | None
    field_values: list[tuple[str, str]]
    field_examples: list[str]

    @override
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Add directive state for Pydantic field data
        self.field_name = ""
        self.field_alias = ""
        self.field_description = None
        self.field_examples = []
        self.field_type = None
        self.field_values = []
        self.deprecation_warning = None
        self.label = ""

    def _create_field_node(self) -> nodes.section:
        """Create a section node using Jinja template for field information.

        This is an alternative implementation using a Jinja template to render
        the field entry as RST, which is then parsed into docutils nodes.

        Returns:
            nodes.section: A section containing well-formed output for each provided field attribute.

        """
        # Set up Jinja environment
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(default_for_string=False),
        )
        template = env.get_template("field-entry.rst.j2")

        # Format examples as YAML strings
        self._format_examples()

        # Render the template
        field_rst = template.render(
            model_name=(self.arguments[0].rsplit(".", maxsplit=1)[-1]).lower(),
            field_name=self.field_alias,
            field_type=self.field_type,
            field_description=self.field_description,
            field_values=self.field_values,
            field_examples=self.field_examples,
            deprecation_warning=self.deprecation_warning,
        )

        # Parse the RST output into docutils nodes
        output_nodes = self._parse_rst(field_rst)

        # The second node in the list is always the section node
        field_node: nodes.section = cast(nodes.section, output_nodes[1])
        # Apply the 'kitbash-entry' CSS class
        field_node["classes"] = ["kitbash-entry"]
        return field_node

    def _format_examples(self) -> None:
        """Create code example with docutils literal_block.

        Creates a literal_block node before populating it with a properly formatted
        YAML string. Outputs warnings whenever invalid YAML is passed.

        Args:
            examples (list[str]): The field examples being formatted.

        Returns:
            list[str]: A list of well-formed YAML examples.

        """
        PrettyListDumper.add_representer(str, str_presenter)
        formatted_examples: list[str] = []

        for example in self.field_examples:
            yaml_example = f"{self.field_alias.rsplit('.', maxsplit=1)[-1]}: {example}"

            if not example.endswith("\n"):
                yaml_example = f"{yaml_example}\n"
            try:
                yaml_str = yaml.dump(
                    yaml.safe_load(yaml_example),
                    Dumper=PrettyListDumper,
                    default_style=None,
                    default_flow_style=False,
                    sort_keys=False,
                )
            except yaml.YAMLError as e:
                warnings.warn(
                    f"Invalid YAML for field {self.name}: {e}",
                    category=UserWarning,
                    stacklevel=2,
                )
                yaml_str = example

            yaml_str = yaml_str.removesuffix("...\n")
            formatted_examples.append(yaml_str)

        self.field_examples = formatted_examples

    def _parse_rst(self, rst: str) -> list[nodes.Node]:
        """Parse rST from model and field docstrings.

        Creates a reStructuredText document node from the given string so that
        the document's child nodes can be appended to the directive's output.
        This function requires the calling directive to enable cross-references,
        which cannot be resolved without a reference to the parent doctree.

        Args:
            rst (str): string containing reStructuredText

        Returns:
            list[Node]: the docutils nodes produced by the rST

        """
        settings = self.state.document.settings
        rst_doc = new_document(self.env.docname, settings=settings)
        rst_parser = Parser()
        rst_parser.parse(inspect.cleandoc(rst), rst_doc)

        return list(rst_doc.children)

    def _generate_label(self) -> None:
        """Create a label for cross-referencing the field.

        Add a label, <model-name>.<field-name> by default, to the inventory file.

        Returns:
            None

        """
        # Default label format: <model-name>.<field-name>
        self.label = self.options.get(
            "label",
            f"{(self.arguments[0].rsplit('.', maxsplit=1)[-1]).lower()}.{self.field_name.lower()}",
        )

        # Add cross-referencing details to `objects.inv`
        self.env.app.env.domaindata["std"]["labels"][self.label] = (
            self.env.docname,  # the document currently being parsed
            self.label,
            self.field_alias,
        )
        self.env.app.env.domaindata["std"]["anonlabels"][self.label] = (
            self.env.docname,
            self.label,
        )

    def _get_optional_field_data(self, annotation: type[Any]) -> None:
        """Traverse the field and retrieve its type, description, and enum values.

        Args:
            field_entry (FieldEntry): Object containing field data.
            annotation (type[Any]): Type annotation of the optional field. This field
                may be either a standard Python type or an optional enum.

        Returns:
            None

        """
        union_args = get_args(annotation)
        self.field_type = format_type_string(union_args[0])
        if isinstance(union_args[0], type) and issubclass(union_args[0], enum.Enum):
            self.field_description = (
                union_args[0].__doc__
                if self.field_description is None
                else self.field_description
            )
            self.field_values = get_enum_values(union_args[0])

    def _get_enum_field_data(self, annotation: type[Any] | None) -> None:
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
            self.field_description = (
                annotation.__doc__
                if self.field_description is None
                else self.field_description
            )
            self.field_values = get_enum_values(annotation)

    def _get_optional_annotated_field_data(self, annotation: type[Any] | None) -> None:
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
                self.field_type = format_type_string(annotated_type.__args__[0])
            metadata = getattr(annotated_type, "__metadata__", None)
            field_annotation = find_fieldinfo(metadata)
            if (
                field_annotation
                and self.field_description is None
                and self.field_examples == []
            ):
                self.field_description = field_annotation.description
                self.field_examples = (
                    field_annotation.examples if field_annotation.examples else []
                )
