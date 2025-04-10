# This file is part of pydantic-kitbash.
#
# Copyright 2023 Canonical Ltd.
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

import pathlib
import sys

project_dir = pathlib.Path("..").resolve()
sys.path.insert(0, str(project_dir.absolute()))

project = "Pydantic Kitbash"
author = "Starcraft Engineering"

html_title = project

extensions = [
    "pydantic_kitbash.directives",
]
