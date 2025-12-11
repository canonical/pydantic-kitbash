# pydantic-kitbash

Kitbash is a Sphinx extension that generates reference documentation for Pydantic
models.

Kitbash parses a model to describe its fields in a Sphinx document. It can target an
entire model or specific fields. When covering a specific field, you can add
reStructuredText to the field's docstring to supplement the standard output.

## Basic usage

The `kitbash-field` directive documents an individual field:

```rst
.. kitbash-field:: my_model my_field
```

The `kitbash-model` directive directive documents an entire model:

```rst
.. kitbash-model:: my_model
```

### Options

#### `skip-examples`

Bypasses the field's examples on the page. Use this when the examples are incomplete or
unhelpful.

```rst
.. kitbash-field:: my_model my_field
    :skip-examples:
```

#### `override-description`

Replaces the field's description with the directive content instead of appending to it.
Use this to modify field descriptions inherited from libraries.

```rst
.. kitbash-field:: upstream_model my_field
    :override-description:

    This text replaces the field's description.

```

#### `override-type`

Overrides the field's type on the page. Use this when the type is overly verbose,
malformed, or unhelpful.

```rst
.. kitbash-field:: my_model my_field
    :override-type: Any
```

#### `prepend-name`

Adds a prefix to the field name on the page. The prefix is separated by a period (.).
This example makes the field render as `permissions.my_field`:

```rst
.. kitbash-field:: my_model my_field
    :prepend-name: permissions
```

#### `append-name`

Adds a suffix to the field name on the page. The suffix is separated by a period (.).
This example makes the field render as `my_field.v1`:

```rst
.. kitbash-field:: my_model my_field
    :append-name: v1
```

#### `label`

Overrides the reStructuredText label for a field. By default, Kitbash adds a label for
each entry, formatted as `<page-filename>-<field-name>`. This example renames the label
to `dev-my-field`:

```rst
.. kitbash-field:: my_model my_field
    :label: dev-my-field
```

### Directive content

By default, directive content is appended to the description. Use this to provide
additional context or information on fields sourced from libraries.

```rst
.. kitbash-field:: my_model my_field

    This is appended to the field's description.

```

If the `override-description` option is included, the directive content will replace the
entire field description.

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
