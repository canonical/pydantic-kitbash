Test output
===========


Field directive
---------------

.. Test default and manual labels

:ref:`Automatic label <index-test>`

.. kitbash-field:: example.project.MockModel mock_field

:ref:`Manual label <cool-beans>`

.. kitbash-field:: example.project.MockModel mock_field
    :label: cool-beans


.. Test internal references in field descriptions and docstrings

.. kitbash-field:: example.project.MockModel xref_desc_test

.. kitbash-field:: example.project.MockModel xref_docstring_test


.. Test multiline examples

.. kitbash-field:: example.project.MockModel block_string


.. Test directive content

.. kitbash-field:: example.project.MockModel mock_field

    This is supplemental information.

    It can contain as many paragraphs of rST as you want.

    :ref:`References <index-test>` work too!

.. kitbash-field:: example.project.MockModel no_desc

    This field has no other description.


.. Test with py:module set

.. py:currentmodule:: example.project

.. kitbash-field:: MockModel mock_field


Model directive
---------------

.. kitbash-model:: MockModel

    This is the model's description.

    It can contain as many paragraphs as you want.


.. toctree::
    :hidden:

    the-other-file
