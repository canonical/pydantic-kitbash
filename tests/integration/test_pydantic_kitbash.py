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
    field_section = soup.find("section", {"class": "kitbash-entry"})
    assert field_section["id"] == "test"

    # Check if heading level is correct
    field_heading = soup.find("h2")
    assert field_heading.text == "test¶"

    # Check if heading contains proper link
    assert field_heading.find("a")["href"] == "#test"

    # Check if admonition is formatted correctly
    deprecation_admonition = soup.find("div", {"class": "admonition important"})
    admonition_content = deprecation_admonition.find_all("p")
    assert admonition_content[0].text == "Important"  # admonition title
    assert admonition_content[1].text == "Deprecated. ew."  # admonition content

    # Check if type is correct
    field_type = soup.find("code", {"class": "docutils literal notranslate"}).text
    assert field_type == "str"

    # Check if YAML example is highlighted correctly
    assert soup.find("span", {"class": "nt"}).text == "test"
    assert soup.find("span", {"class": "p"}).text == ":"
    assert soup.find("span", {"class": "l l-Scalar l-Scalar-Plain"}).text == "val1"

    shutil.rmtree(example_project)
