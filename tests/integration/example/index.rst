Fields
======

.. Test default and manual labels

:ref:`Automatic label <index-test>`

.. kitbash-field:: example.project.MockModel mock_field

:ref:`Manual label <cool-beans>`

.. kitbash-field:: example.project.MockModel mock_field
    :label: cool-beans


.. Test internal references in field descriptions and docstrings

.. kitbash-field:: example.project.MockModel xref_desc_test

.. kitbash-field:: example.project.MockModel xref_docstring_test

.. toctree::
    :hidden:

    the-other-file


.. Test with py:module set

.. py:currentmodule:: example.project

.. kitbash-field:: MockModel mock_field
