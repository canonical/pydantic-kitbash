# This file is part of pydantic-kitbash.
#
# Copyright 2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
# SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime

project = "Kitbash"
author = "Canonical"

copyright = "2025-%s, %s" % (datetime.date.today().year, author)

# Excludes files or directories from processing
exclude_patterns = [
    "tutorials/index.rst",
    "how-to/index.rst",
    "reference/index.rst",
    "explanation/index.rst",
    "release-notes/index.rst",
]

# Type hints configuration
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True

# Github config
github_username = "canonical"
github_repository = "pydantic-kitbash"

# endregion

# Client-side page redirects.
rediraffe_redirects = "redirects.txt"
