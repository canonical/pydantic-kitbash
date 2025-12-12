Test output
===========


Field directive
---------------

.. py:currentmodule:: example.project


.. Test default and manual labels

:ref:`Automatic label <index-test>`

.. kitbash-field:: MockModel mock_field

:ref:`Manual label <cool-beans>`

.. kitbash-field:: MockModel mock_field
    :label: cool-beans


.. Test internal references in field descriptions and docstrings

.. kitbash-field:: MockModel xref_desc_test

.. kitbash-field:: MockModel xref_docstring_test


.. Test multiline examples

.. kitbash-field:: MockModel block_string


.. Test directive content

.. kitbash-field:: MockModel mock_field

    This is supplemental information.

    It can contain as many paragraphs of rST as you want.

    :ref:`References <index-test>` work too!

.. kitbash-field:: MockModel no_desc

    This field has no other description.


.. Test inherited fields

.. kitbash-field:: MockModel parent_field


.. Test description override

.. kitbash-field:: MockModel override_test
    :override-description:

    This is the override.


.. Test docstring paragraph rendering with directive content.

.. kitbash-field:: MockModel docstring_whitespace

    This should not create surprise blockquotes >:(


Model directive
---------------

.. kitbash-model:: MockModel

    This is the model's description.

    It can contain as many paragraphs as you want.


.. toctree::
    :hidden:

    the-other-file
