.. _msl-io-welcome:

======
MSL-IO
======

Read and write MSL data files.

**MSL-IO** follows the data model used by HDF5_, where there is a :class:`~msl.io.root.Root`,
:ref:`group`\'s and :ref:`dataset`\'s and these objects each have :ref:`metadata` associated with them.

.. image:: _static/hdf5_data_model.png

The data files that can be read are not restricted to HDF5_ files, but, rather any
file format that has a :class:`~msl.io.reader.Reader` class implemented can be read.
See :ref:`create-reader` for more details.

To read a data file it is as easy as

.. code-block:: pycon

    >>> from msl.io import read
    >>> root = read('/path/to/some/file.dat')

Provided that a :class:`~msl.io.reader.Reader` exists to read the file a :class:`~msl.io.root.Root`
object is returned.

Since the `root` object is a :ref:`group` (which operates like a Python dictionary) you can inspect the
items that are in the file using

.. code-block:: pycon

    >>> for name, value in root.items():
            print(name, value)

where, `value` will be of type :class:`~msl.io.group.Group` or :class:`~msl.io.dataset.Dataset`.

Or view the metadata for `root`

.. code-block:: pycon

    >>> root.metadata

If you only wanted to see what :class:`~msl.io.group.Group`\'s are in the file

.. code-block:: pycon

    >>> for group in root.groups():
            print(group)

If you only wanted to see what :class:`~msl.io.dataset.Dataset`\'s are in the file

.. code-block:: pycon

    >>> for dataset in root.datasets():
            print(dataset)

When `root` is returned it is accessed, by default, in read-only mode. If you want to edit the
:class:`~msl.io.metadata.Metadata` for `root`, or modify any sub-:class:`~msl.io.group.Group`\'s or
sub-:class:`~msl.io.dataset.Dataset`\'s in `root`, then you must first set the object to be writable.

Setting the read-only mode of `root` propagates that mode to all items within `root`. For example,

.. code-block:: pycon

    >>> root.is_read_only = False

will make `root` and all sub-:class:`~msl.io.group.Group`\'s and all sub-:class:`~msl.io.dataset.Dataset`\'s
within `root` to be writable.

You can make only a specific object (and it's sub objects) writeable as well. Assuming that `root` contains a
:class:`~msl.io.group.Group` called ``'my_group'`` and a :class:`~msl.io.dataset.Dataset` called ``'my_dataset'``
you can make ``'my_dataset'`` writeable by

.. code-block:: pycon

    >>> root['my_dataset'].is_read_only = False

and this will keep `root` and `root['my_group']` in read-only mode.

You can also access the keys in `root` (recall that `root` behaves like a Python dictionary)
as class attributes

.. code-block:: pycon

    >>> root.my_dataset.is_read_only = False

See :ref:`attribute-key-limitations` for more information.

========
Contents
========

.. toctree::
   :maxdepth: 1

   Group <group>
   Dataset <dataset>
   Metadata <metadata>
   new_reader
   API <api_docs>
   attribute_access
   License <license>
   Authors <authors>
   Release Notes <changelog>

=====
Index
=====

* :ref:`modindex`


.. _HDF5: https://portal.hdfgroup.org/display/support
