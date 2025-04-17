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

"""Contains the core elements of pydantic-kitbash."""

from sphinx.util.typing import ExtensionMetadata
from sphinx.application import Sphinx
from pydantic_kitbash.directives import KitbashFieldDirective, KitbashModelDirective


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up the sphinx extension.

    Args:
      app (Sphinx): Sphinx application

    Returns:
      ExtensionMetadata: Extension metadata

    """
    app.add_directive("kitbash-field", KitbashFieldDirective)
    app.add_directive("kitbash-model", KitbashModelDirective)

    return {
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
