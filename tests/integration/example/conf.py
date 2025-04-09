from datetime import datetime
import os
import pathlib
import sys


sys.path.append(str(pathlib.Path('_ext').resolve()))

project = "Pydantic Kitbash"
author = "Starcraft Engineering"

html_title = project

extensions = [
    "pydantic-kitbash",
]
