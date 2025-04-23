# pydantic-kitbash

Kitbash is a Sphinx extension that automates the generation of reference documentation
for Pydantic models.

Kitbash parses a model to describe its fields in a Sphinx document. It can target an
entire model or specific fields. When covering a specific field, you can add
reStructuredText to the field's docstring to supplement the standard output.

## Basic usage

To document an individual field, add the `kitbash-field` directive to your document:

```
.. kitbash-field:: <model-name> <field-name>
```

If you'd prefer to document an entire model, add the `kitbash-model` directive to your
document:

```
.. kitbash-model:: <model-name>
```

## Project setup

Kitbash is published on PyPI and can be installed with:

```bash
pip install pydantic-kitbash
```

After adding Kitbash to your Python project, update Sphinx's `conf.py` file to include
Kitbash as one of its extensions:

```python
extensions = [
    "pydantic_kitbash",
]
```

## Community and support

You can report any issues or bugs on the project's [GitHub
repository](https://github.com/canonical/pydantic-kitbash/issues).

Kitbash is covered by the [Ubuntu Code of
Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## License and copyright

Kitbash is released under the [LGPL-3.0 license](LICENSE).

@ 2025 Canonical Ltd.
