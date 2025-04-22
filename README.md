# pydantic-kitbash

Kitbash is a Sphinx extension that automates the generation of reference documentation
for Pydantic models.

As it traverses a model, Kitbash collects field data and generates consistent,
well-formed output to be included in your product's documentation. To supplement this
information, you can add Python docstrings below fields, which Kitbash will parse as
reStructuredText to be included in the field's description.

## Basic usage

To document an individual field, add the `kitbash-field` directive to your rST document:

```
.. kitbash-field:: <model-name> <field-name>
```

If you'd prefer to document an entire model, add the `kitbash-model` directive to your
rST document:

```
.. kitbash-model:: <model-name>
```

This will create an entry for each of the model's fields in the order they're defined.

## Project setup

To add Kitbash to your project, add `pydantic-kitbash` to the appropriate dependency
group in your pyproject.toml file:

```toml
[dependency-groups]
docs = [
    "pydantic-kitbash",
    ...
]
```

After adding Kitbash to your Python project, update Sphinx's `conf.py` file to include
Kitbash:

```python
extensions = [
    "pydantic_kitbash",
    ...
]
```

## Community and support

You can report any issues or bugs on the project's [GitHub
repository](https://github.com/canonical/pydantic-kitbash/issues).

Kitbash is covered by the [Ubuntu Code of
Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## License and copyright

Kitbash is released under the [LGPL-3.0 license](LICENSE).

@2025 Canonical Ltd.
