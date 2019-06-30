.. _msl-io-group:

=====
Group
=====
A :class:`~msl.io.group.Group` is analogous to a directory on your operating system. A :class:`~msl.io.group.Group`
can contain any number of sub-:class:`~msl.io.group.Group`\s (i.e., subdirectories) and it can contain any number
of :ref:`msl-io-dataset`\s. It uses a naming convention analogous to UNIX file systems where every subdirectory is
separated from its parent directory by the ``'/'`` character.

From a Python perspective, a :class:`~msl.io.group.Group` operates like a dictionary. The `keys` are
the names of :class:`~msl.io.group.Group` members, and the `values` are the members themselves
(:class:`~msl.io.group.Group` and :class:`~msl.io.dataset.Dataset`) objects.

A :class:`~msl.io.group.Group` can be in read-only mode and the `keys` of a :class:`~msl.io.group.Group` can
be accessed as class attributes (see :ref:`attribute-key-limitations` for more information).
