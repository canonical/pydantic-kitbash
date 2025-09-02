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

import shutil
import subprocess
from pathlib import Path
from typing import cast

import bs4
import pytest


def get_field_description(
    field_id: str, idx: int, soup: bs4.BeautifulSoup
) -> bs4.element.PageElement:
    field_entry = soup.find("section", id=field_id)

    desc = bs4.element.PageElement()
    if field_entry:
        field_contents = field_entry.find_all_next("p")
        return field_contents[3]

    return desc


@pytest.fixture
def example_project(request) -> Path:
    project_root = request.config.rootpath
    example_dir = project_root / "tests/integration/example"

    # Copy the project into the test's own temporary dir, to avoid clobbering
    # the sources.
    target_dir = Path().resolve() / "example"
    shutil.copytree(example_dir, target_dir, dirs_exist_ok=True)

    return target_dir


@pytest.mark.slow
def test_pydantic_kitbash_integration(example_project):
    build_dir = example_project / "_build"
    subprocess.check_call(
        ["sphinx-build", "-b", "html", "-W", example_project, build_dir],
    )

    index = build_dir / "index.html"

    # Rename the test output to something more meaningful
    shutil.copytree(
        build_dir, build_dir.parents[1] / ".test_output", dirs_exist_ok=True
    )

    soup = bs4.BeautifulSoup(index.read_text(), features="lxml")
    shutil.rmtree(example_project)  # Delete copied source

    # Check if field entry was created
    assert soup.find("section", {"class": "kitbash-entry"})

    # Check if heading level is correct and contains proper link
    field_heading = soup.find("h3")
    if field_heading:
        assert getattr(field_heading, "text", None) == "test¶"
    else:
        pytest.fail("Field heading not found")

    # Check if admonition is formatted correctly
    deprecation_admonition = soup.find("div", {"class": "admonition important"})
    if isinstance(deprecation_admonition, bs4.Tag):
        admonition_content = deprecation_admonition.find_all("p")
        assert admonition_content[0].text == "Important"  # admonition title
        assert admonition_content[1].text == "Deprecated. ew."  # admonition content

    # Check if type is present and correct
    type_literal_block = soup.find("code", {"class": "docutils literal notranslate"})
    if type_literal_block:
        field_prefix = type_literal_block.previous_sibling
        field_type = getattr(type_literal_block, "text", None)
        assert field_prefix == "One of: "
        assert field_type == "['val1', 'val2']"
    else:
        pytest.fail("Type not found in rendered output")

    # Check if YAML example is highlighted correctly
    assert getattr(soup.find("span", {"class": "nt"}), "text", None) == "test"
    assert getattr(soup.find("span", {"class": "p"}), "text", None) == ":"
    assert (
        getattr(soup.find("span", {"class": "l l-Scalar l-Scalar-Plain"}), "text", None)
        == "val1"
    )

    # Ensure that the internal reference from the field's description was created
    assert get_field_description("xref_desc_test", 3, soup).find_next(
        "span", {"class": "std std-ref"}
    )  # The description body is the third paragraph in the section

    # Ensure that the internal reference from the field's docstring was created
    assert get_field_description("xref_docstring_test", 3, soup).find_next(
        "span", {"class": "std std-ref"}
    )

    # Ensure that PyYAML doesn't mangle the whitespace in multiline examples.
    block_string_entry = soup.find("section", id="block_string")
    if block_string_entry:
        multiline_yaml_example = block_string_entry.find_next(
            "div", {"class": "highlight-yaml notranslate"}
        )  # grab the field entry's example
        multiline_yaml_example = cast(bs4.Tag, multiline_yaml_example)
        if multiline_yaml_example:
            # There should be 4 occurrences of whitespace (including the first line)
            assert len(multiline_yaml_example.find_all("span", {"class": "w"})) == 4
        else:
            pytest.fail("Multiline YAML example not found in output.")
    else:
        pytest.fail("block_string entry not found in output.")

    # Check that directive content renders correctly when the field description is 'None'
    assert (
        getattr(get_field_description("no_desc", 3, soup), "text", None)
        == "This field has no other description."
    )
