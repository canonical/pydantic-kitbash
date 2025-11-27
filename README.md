# pydantic-kitbash

Kitbash is a Sphinx extension that automates the generation of reference documentation
for Pydantic models.

Kitbash parses a model to describe its fields in a Sphinx document. It can target an
entire model or specific fields. When covering a specific field, you can add
reStructuredText to the field's docstring to supplement the standard output.

## Basic usage

To document an individual field, add the `kitbash-field` directive to your document:

```rst
.. kitbash-field:: <model-name> <field-name>
```

If you'd prefer to document an entire model, add the `kitbash-model` directive to your
document:

```rst
.. kitbash-model:: <model-name>
```

### Options

If a field's examples aren't needed, skip them:

```rst
.. kitbash-field:: <model-name> <field-name>
    :skip-examples:
```

If the field's type is overly verbose, malformed, or unhelpful, override it:

```rst
.. kitbash-field:: <model-name> <field-name>
    :override-type: Any
```

You can add to the start of the field's name in the document. For example, to make
`my-field` become `permissions.my-field`, use:

```rst
.. kitbash-field:: <model-name> my_field
    :prepend-name: permissions
```

You can add to the end of the field's name in the document. For example, to make
`my-field` become `my-field.v1`, use:

```rst
.. kitbash-field:: <model-name> my_field
    :append-name: v1
```

Kitbash automatically add a Sphinx target for each entry. The target names follow the
format `<page-filename>-<field-name>`. You can override this as well:

```rst
.. kitbash-model:: <model-name>
    :label: new-model

.. kitbash-field:: <model-name> <field-name>
    :label: new-field
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
