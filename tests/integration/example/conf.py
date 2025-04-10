import pathlib
import sys

sys.path.append(str(pathlib.Path("_ext").resolve()))
print(sys.path)

project = "Pydantic Kitbash"
author = "Starcraft Engineering"

html_title = project

extensions = [
    "kitbash",
]
