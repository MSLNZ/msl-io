.. _msl-io-welcome:

======
MSL-IO
======
**MSL-IO** follows the data model used by HDF5_ to read and write data files -- where there is a
:class:`~msl.io.base.Root`, :ref:`msl-io-group`\s and :ref:`msl-io-dataset`\s and these objects
each have :ref:`msl-io-metadata` associated with them.

.. image:: _static/hdf5_data_model.png

The tree structure is similar to the file-system structure used by operating systems. :ref:`msl-io-group`\s
are analogous to the directories (where :class:`~msl.io.base.Root` is the root :ref:`msl-io-group`) and
:ref:`msl-io-dataset`\s are analogous to the files.

The data files that can be read or created are not restricted to HDF5_ files, but any file format that
has a :ref:`Reader <io-readers>` implemented can be read and data files can be created using any of the
:ref:`Writers <io-writers>`.

Getting Started
---------------

* :ref:`msl-io-write`
* :ref:`msl-io-read`
* :ref:`msl-io-convert`
* :ref:`msl-io-read-table`

.. invisible-code-block: pycon

   >>> from pathlib import Path
   >>> Path("my_file.h5").unlink(missing_ok=True)
   >>> Path("my_file.json").unlink(missing_ok=True)
   >>> Path("my_table.csv").unlink(missing_ok=True)
   >>> SKIP_IF_PYTHON_LESS_THAN_36() or SKIP_IF_NO_H5PY()

.. _msl-io-write:

Write a file
------------
Suppose you want to create a new HDF5_ file. We first create an instance of
:class:`~msl.io.writers.hdf5.HDF5Writer`

.. code-block:: pycon

   >>> from msl.io import HDF5Writer
   >>> h5 = HDF5Writer()

then we can add :class:`~msl.io.metadata.Metadata` to the :class:`~msl.io.base.Root`,

.. code-block:: pycon

   >>> h5.add_metadata(one=1, two=2)

create a :class:`~msl.io.dataset.Dataset` in the :class:`~msl.io.base.Root`,

.. code-block:: pycon

   >>> dataset1 = h5.create_dataset('dataset1', data=[1, 2, 3, 4])

create a :class:`~msl.io.group.Group` in the :class:`~msl.io.base.Root`,

.. code-block:: pycon

   >>> my_group = h5.create_group('my_group')

and create a :class:`~msl.io.dataset.Dataset` in *my_group*

.. code-block:: pycon

   >>> dataset2 = my_group.create_dataset('dataset2', data=[[1, 2], [3, 4]], three=3)

Finally, we write the file

.. code-block:: pycon

   >>> h5.write(file='my_file.h5')

.. note::

   The file is not created until you call the :meth:`~msl.io.base.Writer.write` or
   :meth:`~msl.io.base.Writer.save` method.

.. _msl-io-read:

Read a file
------------
The :func:`~msl.io.read` function is available to read a file. Provided that a :ref:`Reader <io-readers>`
exists to read the file a :class:`~msl.io.base.Root` object is returned. We will read the file
that we created above.

.. code-block:: pycon

    >>> from msl.io import read
    >>> root = read('my_file.h5')

You can print a representation of all :class:`~msl.io.group.Group`\s and :class:`~msl.io.dataset.Dataset`\s
in the :class:`~msl.io.base.Root` by calling the :meth:`~msl.io.base.Root.tree` method

.. code-block:: pycon

    >>> print(root.tree())
    <HDF5Reader 'my_file.h5' (1 groups, 2 datasets, 2 metadata)>
      <Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
      <Group '/my_group' (0 groups, 1 datasets, 0 metadata)>
        <Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

Since the *root* object is a :ref:`msl-io-group` (which operates like a Python :class:`dict`) you can
iterate over the items that are in the file using

.. code-block:: pycon

    >>> for name, value in root.items():
    ...     print('{!r} -- {!r}'.format(name, value))
    '/dataset1' -- <Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
    '/my_group' -- <Group '/my_group' (0 groups, 1 datasets, 0 metadata)>
    '/my_group/dataset2' -- <Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

where *value* will either be a :class:`~msl.io.group.Group` or a :class:`~msl.io.dataset.Dataset`.

You can iterate over the :ref:`msl-io-group`\s that are in the file

.. code-block:: pycon

    >>> for group in root.groups():
    ...     print(group)
    <Group '/my_group' (0 groups, 1 datasets, 0 metadata)>

or iterate over the :ref:`msl-io-dataset`\s

.. code-block:: pycon

    >>> for dataset in root.datasets():
    ...     print(repr(dataset))
    <Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
    <Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

You can access the :ref:`msl-io-metadata` of any object through the :obj:`~msl.io.vertex.Vertex.metadata` attribute

.. code-block:: pycon

    >>> print(root.metadata)
    <Metadata '/' {'one': 1, 'two': 2}>

You can access values of the :ref:`msl-io-metadata` as attributes

.. code-block:: pycon

   >>> print(root.metadata.one)
   1
   >>> dataset2.metadata.three
   3

or as keys

.. code-block:: pycon

   >>> print(root.metadata['two'])
   2
   >>> dataset2.metadata['three']
   3

When *root* is returned it is accessed in read-only mode

.. code-block:: pycon

    >>> root.read_only
    True
    >>> for name, value in root.items():
    ...     print('is {!r} in read-only mode? {}'.format(name, value.read_only))
    is '/dataset1' in read-only mode? True
    is '/my_group' in read-only mode? True
    is '/my_group/dataset2' in read-only mode? True

If you want to edit the :class:`~msl.io.metadata.Metadata` for *root*, or modify any
:class:`~msl.io.group.Group`\s or :class:`~msl.io.dataset.Dataset`\s in *root*, then you must first set
the object to be editable. Setting the read-only mode of *root* propagates that mode to all items within
*root*. For example,

.. code-block:: pycon

    >>> root.read_only = False

will make *root* and all :ref:`msl-io-group`\s and all :ref:`msl-io-dataset`\s within *root* to be editable

.. code-block:: pycon

    >>> root.read_only
    False
    >>> for name, value in root.items():
    ...     print('is {!r} in read-only mode? {}'.format(name, value.read_only))
    is '/dataset1' in read-only mode? False
    is '/my_group' in read-only mode? False
    is '/my_group/dataset2' in read-only mode? False

You can make only a specific object (and it's descendants) editable as well. You can make
*my_group* and *dataset2* to be in read-only mode by the following (recall that *root* behaves
like a Python :class:`dict`)

.. code-block:: pycon

    >>> root['my_group'].read_only = True

and this will keep *root* and *dataset1* in editable mode, but change *my_group* and *dataset2*
to be in read-only mode

.. code-block:: pycon

    >>> root.read_only
    False
    >>> for name, value in root.items():
    ...     print('is {!r} in read-only mode? {}'.format(name, value.read_only))
    is '/dataset1' in read-only mode? False
    is '/my_group' in read-only mode? True
    is '/my_group/dataset2' in read-only mode? True

You can access the :ref:`msl-io-group`\s and :ref:`msl-io-dataset`\s as keys or as class attributes

.. code-block:: pycon

    >>> root['my_group']['dataset2'].shape
    (2, 2)
    >>> root.my_group.dataset2.shape
    (2, 2)

See :ref:`attribute-key-limitations` for more information.

.. _msl-io-convert:

Convert a file
--------------
You can convert between file formats using any of the :ref:`Writers <io-writers>`.
Suppose you had an HDF5_ file and you wanted to convert it to the JSON_ format

.. code-block:: pycon

   >>> from msl.io import JSONWriter
   >>> h5 = read('my_file.h5')
   >>> writer = JSONWriter('my_file.json')
   >>> writer.write(root=h5)

.. _msl-io-read-table:

Read data in a table
--------------------
The :func:`~msl.io.read_table` function is available to read a table from a file.

A *table* has the following properties:

1. The first row is a header.
2. All rows have the same number of columns.
3. All data values in a column have the same data type.

The returned object is a :class:`~msl.io.dataset.Dataset` with the header provided as metadata.

Suppose a file called *my_table.csv* contains the following information

.. raw:: html

   <table>
     <tr>
       <th>x,</th>
       <th>y,</th>
       <th>z</th>
     </tr>
     <tr>
       <td>1,</td>
       <td>2,</td>
       <td>3</td>
     </tr>
     <tr>
       <td>4,</td>
       <td>5,</td>
       <td>6</td>
     </tr>
     <tr>
       <td>7,</td>
       <td>8,</td>
       <td>9</td>
     </tr>
   </table>
   </br>

.. invisible-code-block: pycon

   >>> with open('my_table.csv', mode='wt') as f:
   ...    for row in [['x','y','z'],[1,2,3],[4,5,6],[7,8,9]]:
   ...        dump = f.write(','.join(str(item) for item in row) + '\n')

You can read this file and interact with the data using the following

.. code-block:: pycon

    >>> from msl.io import read_table
    >>> csv = read_table('my_table.csv')
    >>> csv
    <Dataset 'my_table.csv' shape=(3, 3) dtype='<f8' (1 metadata)>
    >>> csv.metadata
    <Metadata 'my_table.csv' {'header': ['x' 'y' 'z']}>
    >>> csv.data
    array([[1., 2., 3.],
           [4., 5., 6.],
           [7., 8., 9.]])
    >>> print(csv.max())
    9.0

You can read a table from a text-based file or from an Excel spreadsheet.

.. invisible-code-block: pycon

   >>> import os
   >>> os.remove('my_file.h5')
   >>> os.remove('my_file.json')
   >>> os.remove('my_table.csv')

========
Contents
========

.. toctree::
   :maxdepth: 1

   Install <install>
   Group <group>
   Dataset <dataset>
   Metadata <metadata>
   readers
   writers
   API <api_docs>
   attribute_access
   License <license>
   Authors <authors>
   Release Notes <changelog>

=====
Index
=====

* :ref:`modindex`


.. _HDF5: https://www.hdfgroup.org/
.. _JSON: https://www.json.org/
