# pydantic-kitbash

Kitbash is a Sphinx extension that automates the generation of reference documentation
for Pydantic models.

Kitbash parses a model to describe its fields in a Sphinx document. It can target an
entire model or specific fields. When covering a specific field, you can add
reStructuredText to the field's docstring to supplement the standard output.

## Basic usage

The `kitbash-field` directive documents an individual field:

```rst
.. kitbash-field:: my-model my-field
```

The `kitbash-model` directive directive documents an entire model:

```rst
.. kitbash-model:: my-model
```

### Options

#### `skip-examples`

Bypasses the field's examples on the page. Use this when the examples are incomplete or
unhelpful.

```rst
.. kitbash-field:: my-model my-field
    :skip-examples:
```

#### `override-type`

Overrides the field's type on the page. Use this when the type is overly verbose,
malformed, or unhelpful.

```rst
.. kitbash-field:: my-model my-field
    :override-type: Any
```

#### `prepend-name`

Adds a prefix to the field name on the page. The prefix is separated by a period (.).
This example makes the field render as `permissions.my-field`:

```rst
.. kitbash-field:: my-model my-field
    :prepend-name: permissions
```

#### `append-name`

Adds a suffix to the field name on the page. The prefix is separated by a period (.).
This example makes the field render as `my-field.v1`:

```rst
.. kitbash-field:: my-model my-field
    :append-name: v1
```

#### `label`

Overrides the Sphinx label prefix for a field. By default, Kitbash adds a Sphinx label
for each entry. The labels have the format `<page-filename>-<field-name>`. This example rewrites the label as `dev-my-field`:

```rst
.. kitbash-field:: my-model my_field
    :label: dev
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
