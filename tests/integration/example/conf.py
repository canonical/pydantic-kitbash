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
