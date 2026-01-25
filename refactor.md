# The great Kitbash refactor

This one may have gotten away from me, but I think these changes do a lot for the
overall code quality.

## base.py

I turned `FieldEntry` into a parent `KitbashDirective` and turned all of the
node construction functions into `KitbashDirective` methods. These functions were all tightly coupled to the `FieldEntry` class, so it makes more sense for them to be
methods.

- `directives.create_field_node` -> `base.KitbashDirective.create_field_node`
- `directives.create_table_node` -> `base.KitbashDirective.create_table_node`
- `directives.create_table_row` incorporated into
  `base.KitbashDirective.create_table_node`
- `directives.build_examples_block` -> `base.KitbashDirective.build_examples_block`
- `directives.parse_rst_description` -> `base.KitbashDirective.parse_rst_description`
- Label registration was separated into `base.KitbashDirective.generate_label`, as it
  was common to both directives.
- `directives.get_optional_annotated_field_data` ->

I also moved the `PrettyListDumper` class and `str_presenter` function into this file,
as they're only used in `build_examples_block`. Their contents are unchanged.

- `directives.PrettyListDumper` -> `base.PrettyListDumper`
- `directives.str_presenter` -> `base.str_presenter`

## utils.py

I moved any functions that weren't coupled to an individual field/directive into a new
`utils.py` file. This included:

- `get_pydantic_model`
- `find_fieldinfo`
- `is_deprecated`
- `get_enum_values`
- `get_enum_member_docstring`
- `is_enum_type`
- `get_annotation_docstring`
- `format_type_string`
