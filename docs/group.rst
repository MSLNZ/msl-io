.. _msl-io-group:

=====
Group
=====
A :class:`~msl.io.group.Group` is analogous to a directory for an operating system. A :class:`~msl.io.group.Group`
can contain any number of sub-:class:`~msl.io.group.Group`\s (i.e., sub-directories) and it can contain any number
of :ref:`msl-io-dataset`\s. It uses a naming convention analogous to UNIX file systems where every sub-directory is
separated from its parent directory by the ``'/'`` character.

From a Python perspective, a :class:`~msl.io.group.Group` operates like a :class:`dict`. The `keys` are
the names of :class:`~msl.io.group.Group` members, and the *values* are the members themselves
(:class:`~msl.io.group.Group` or :class:`~msl.io.dataset.Dataset` objects).

.. invisible-code-block: pycon

   >>> SKIP_IF_PYTHON_LESS_THAN_36()
   >>> from msl.io import JSONWriter
   >>> root = JSONWriter('example.json')
   >>> c = root.create_group('a/b/c')
   >>> b = root.a.b
   >>> dset = c.create_dataset('dset', data=list(range(100)))
   >>> root.read_only = True

.. code-block:: pycon

   >>> print(root.tree())
    <JSONWriter 'example.json' (3 groups, 1 datasets, 0 metadata)>
      <Group '/a' (2 groups, 1 datasets, 0 metadata)>
        <Group '/a/b' (1 groups, 1 datasets, 0 metadata)>
          <Group '/a/b/c' (0 groups, 1 datasets, 0 metadata)>
            <Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>

A :class:`~msl.io.group.Group` can be in read-only mode, but can also be set to editable mode

.. code-block:: pycon

   >>> b.create_dataset('dset_b', data=[1, 2, 3, 4])
   Traceback (most recent call last):
     ...
   ValueError: Cannot modify <Group '/a/b' (1 groups, 1 datasets, 0 metadata)>. It is accessed in read-only mode.
   >>> b.read_only = False
   >>> b.create_dataset('dset_b', data=[1, 2, 3, 4])
   <Dataset '/a/b/dset_b' shape=(4,) dtype='<f8' (0 metadata)>

The *keys* of a :class:`~msl.io.group.Group` can also be accessed as class attributes

.. code-block:: pycon

   >>> root['a']['b']['c']['dset']
   <Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>
   >>> root.a.b.c.dset
   <Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>

See :ref:`attribute-key-limitations` for more information.

You can navigate through the tree by considering a :class:`~msl.io.group.Group` to be an ancestor
or descendant of other :class:`~msl.io.group.Group`\s

.. code-block:: pycon

   >>> for ancestor in c.ancestors():
   ...    print(ancestor)
    <Group '/a/b' (1 groups, 2 datasets, 0 metadata)>
    <Group '/a' (2 groups, 2 datasets, 0 metadata)>
    <JSONWriter 'example.json' (3 groups, 2 datasets, 0 metadata)>
   >>> for descendant in b.descendants():
   ...    print(descendant)
    <Group '/a/b/c' (0 groups, 1 datasets, 0 metadata)>
