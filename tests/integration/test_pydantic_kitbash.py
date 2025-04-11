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

import bs4
import pytest


@pytest.fixture
def example_project(request) -> Path:
    project_root = request.config.rootpath
    example_dir = project_root / "tests/integration/example"

    # Copy the project into the test's own temporary dir, to avoid clobbering
    # the sources.
    target_dir = Path().resolve() / "example"
    shutil.copytree(example_dir, target_dir)

    return target_dir


@pytest.mark.slow
def test_pydantic_kitbash_integration(example_project):
    build_dir = example_project / "_build"
    subprocess.check_call(
        ["sphinx-build", "-b", "html", "-W", example_project, build_dir],
    )

    index = build_dir / "index.html"
    soup = bs4.BeautifulSoup(index.read_text(), features="lxml")

    # Check if field entry was created
    assert soup.find("section", {"class": "kitbash-entry"})

    # Check if heading level is correct and contains proper link
    field_heading = soup.find("h2")
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

    # Check if type is correct
    field_type = getattr(
        soup.find("code", {"class": "docutils literal notranslate"}), "text", None
    )
    assert field_type == "str"

    # Check if YAML example is highlighted correctly
    assert getattr(soup.find("span", {"class": "nt"}), "text", None) == "test"
    assert getattr(soup.find("span", {"class": "p"}), "text", None) == ":"
    assert (
        getattr(soup.find("span", {"class": "l l-Scalar l-Scalar-Plain"}), "text", None)
        == "val1"
    )

    shutil.rmtree(example_project)
