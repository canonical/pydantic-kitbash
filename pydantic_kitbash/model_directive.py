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

"""Define core functions of the kitbash-model directive."""

from types import UnionType
from typing import Union, get_origin

from docutils import nodes
from docutils.parsers.rst import directives

from pydantic_kitbash.base import KitbashDirective
from pydantic_kitbash.utils import (
    format_type_string,
    get_annotation_docstring,
    get_pydantic_model,
    is_deprecated,
    is_enum_type,
)


class KitbashModelDirective(KitbashDirective):
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

        Returns:
            list[nodes.Node]: Well-formed list of nodes to render into field entries.

        """
        # Get the target model, specified by `self.arguments[0]`
        py_module = self.env.ref_context.get("py:module", "")
        target_model = get_pydantic_model(py_module, self.arguments[0], "")

        class_node: list[nodes.Node] = []

        # User-provided description overrides model docstring
        if self.content:
            class_node += self._parse_rst_description("\n".join(self.content))
        elif target_model.__doc__ and "skip-description" not in self.options:
            class_node += self._parse_rst_description(target_model.__doc__)

        # Check if user provided a list of deprecated fields to include
        include_deprecated = [
            field.strip()
            for field in self.options.get("include-deprecated", "").split(",")
        ]

        for field in target_model.model_fields:
            # Get the source model for the field
            pydantic_model = get_pydantic_model(py_module, self.arguments[0], field)

            deprecation_warning = (
                is_deprecated(pydantic_model, field)
                if not field.startswith(("_", "model_"))
                else None
            )

            if (
                not field.startswith(("_", "model_"))
                and deprecation_warning is None
                or field in include_deprecated
            ):
                # grab pydantic field data (need desc and examples)
                field_params = pydantic_model.model_fields[field]

                self.field_name = field
                self.field_alias = (
                    field_params.alias if field_params.alias else self.field_name
                )
                self.deprecation_warning = deprecation_warning

                self.field_description = get_annotation_docstring(
                    pydantic_model, self.field_name
                )
                # Use JSON description value if docstring doesn't exist
                self.field_description = (
                    field_params.description
                    if self.field_description is None
                    else self.field_description
                )

                self.field_examples = field_params.examples

                # if field is optional "normal" type (e.g., str | None)
                if (
                    field_params.annotation
                    and get_origin(field_params.annotation) is UnionType
                ):
                    self._get_optional_field_data(field_params.annotation)
                else:
                    self.field_type = format_type_string(field_params.annotation)

                # if field is optional annotated type (e.g., `VersionStr | None`)
                if (
                    field_params.annotation
                    and get_origin(field_params.annotation) is Union
                ):
                    self._get_optional_annotated_field_data(field_params.annotation)
                elif is_enum_type(field_params.annotation):
                    self._get_enum_field_data(field_params.annotation)

                # Get strings to concatenate with `field_alias`
                name_prefix = self.options.get("prepend-name", "")
                name_suffix = self.options.get("append-name", "")

                # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
                self.field_alias = (
                    f"{name_prefix}.{self.field_alias}"
                    if name_prefix
                    else self.field_alias
                )
                self.field_alias = (
                    f"{self.field_alias}.{name_suffix}"
                    if name_suffix
                    else self.field_alias
                )

                self._generate_label()

                class_node.append(self._create_field_node())

                # Clean up directive state between fields
                self._clean_instance_fields()

        return class_node

    def _clean_instance_fields(self) -> None:
        """Set instance fields to their default.

        This is to prevent any data carrying from one field entry
        to the next.
        """
        self.field_name = ""
        self.field_alias = ""
        self.field_description = None
        self.field_examples = None
        self.field_type = None
        self.field_values = []
        self.deprecation_warning = None
        self.label = ""
