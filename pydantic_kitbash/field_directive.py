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

"""Define core functions of the kitbash-field directive."""

import inspect
from types import UnionType
from typing import Union, get_origin

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.errors import ExtensionError

from pydantic_kitbash.base import KitbashDirective
from pydantic_kitbash.utils import (
    format_type_string,
    get_annotation_docstring,
    get_pydantic_model,
    is_deprecated,
    is_enum_type,
)


class KitbashFieldDirective(KitbashDirective):
    """Define the kitbash-field directive's data and behavior."""

    required_arguments = 2
    has_content = True
    final_argument_whitespace = True

    option_spec = {
        "skip-examples": directives.flag,
        "override-description": directives.flag,
        "override-type": directives.unchanged,
        "prepend-name": directives.unchanged,
        "append-name": directives.unchanged,
        "label": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Generate an entry for the provided field.

        Access the docstring and data from a user-provided Pydantic field
        to produce a formatted output in accordance with Starcraft's YAML key
        documentation standard.

        Returns:
            list[nodes.Node]: Well-formed list of nodes to render into field entry.

        """
        self._init_fields()

        pydantic_model = get_pydantic_model(
            self.env.ref_context.get("py:module", ""),
            self.arguments[0],
            self.arguments[1],
        )

        self.field_name = self.arguments[1]
        self.field_alias = self.arguments[1]

        # grab pydantic field data
        field_params = pydantic_model.model_fields[self.field_name]

        self.field_alias = field_params.alias if field_params.alias else self.field_name

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
        if field_params.annotation and get_origin(field_params.annotation) is UnionType:
            self._get_optional_field_data(field_params.annotation)
        else:
            self.field_type = format_type_string(field_params.annotation)

        # if field is optional annotated type (e.g., VersionStr | None)
        if get_origin(field_params.annotation) is Union:
            self._get_optional_annotated_field_data(field_params.annotation)
        elif is_enum_type(field_params.annotation):
            self._get_enum_field_data(field_params.annotation)

        self.deprecation_warning = is_deprecated(pydantic_model, self.field_name)

        if (
            "override-description" in self.options
        ):  # replace description with directive content
            if not self.content:
                raise ExtensionError(
                    "Directive content must be included alongside the 'override-description' option."
                )
            self.field_description = "\n".join(self.content)
        elif self.content:  # append directive content to description
            supplemental_description = "\n".join(self.content)
            self.field_description = (
                # Dedent description before appending directive content so that
                # it doesn't set the lowest indentation level.
                f"{inspect.cleandoc(self.field_description)}\n\n{supplemental_description}"
                if self.field_description
                else supplemental_description
            )

        # Replace type if :override-type: directive option was used
        self.field_type = self.options.get("override-type", self.field_type)

        # Remove examples if :skip-examples: directive option was used
        self.field_examples = (
            None if "skip-examples" in self.options else self.field_examples
        )

        # Get strings to concatenate with `field_alias`
        name_prefix = self.options.get("prepend-name", "")
        name_suffix = self.options.get("append-name", "")

        # Concatenate option values in the form <prefix>.{field_alias}.<suffix>
        self.field_alias = (
            f"{name_prefix}.{self.field_alias}" if name_prefix else self.field_alias
        )
        self.field_alias = (
            f"{self.field_alias}.{name_suffix}" if name_suffix else self.field_alias
        )

        self._generate_label()

        return [self._create_field_node()]
