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

from typing import Literal

import pydantic


class MockModel(pydantic.BaseModel):
    mock_field: Literal["val1", "val2"] = pydantic.Field(
        description="description",
        examples=["val1", "val2"],
        alias="test",
        deprecated="ew.",
    )

    no_desc: str

    xref_desc_test: str = pydantic.Field(description=":ref:`the-other-file`")

    xref_docstring_test: str = pydantic.Field(description="ignored")
    """:ref:`the-other-file`"""

    block_string: str = pydantic.Field(
        description="this has a multiline example",
        examples=[
            """
            |
              wow
              so many
              lines"""
        ],
    )
