.. _msl-io-metadata:

========
Metadata
========
All :ref:`msl-io-group` and :ref:`msl-io-dataset` objects contain :class:`~msl.io.metadata.Metadata`. A
:class:`~msl.io.metadata.Metadata` object is a :class:`dict` that can be made read only and allows
for accessing the keys of the :class:`dict` as class attributes (see :ref:`attribute-key-limitations` for
more information).

For example, suppose that a file is read with the `root` :ref:`msl-io-group` having the following
:class:`~msl.io.metadata.Metadata`

.. code-block:: pycon

    >>> from msl.io import read
    >>> root = read('/path/to/some/file.dat')
    >>> root.metadata
    {'voltage': 1.2, 'voltage_units': 'V'}

The values in `root.metadata` can be accessed as keys

.. code-block:: pycon

    >>> root.metadata['voltage']
    1.2

or as attributes

.. code-block:: pycon

    >>> root.metadata.voltage
    1.2

Since, by default, `root` is returned in read-only mode you cannot modify the metadata

.. code-block:: pycon

    >>> root.metadata.voltage = 7.64
    ...
    ValueError: Cannot modify <Metadata id=0x1edf606ccf8 name=/>. It is accessed in read-only mode.
    >>> root.add_metadata(current=10.3, current_units='mA')
    ...
    ValueError: Cannot modify <Metadata id=0x1edf606ccf8 name=/>. It is accessed in read-only mode.

However, you can allow `root.metadata` to be modified by setting the :obj:`~msl.io.dictionary.Dictionary.is_read_only`
property to be :data:`False`

.. code-block:: pycon

    >>> root.metadata.is_read_only = False
    >>> root.metadata.voltage = 7.64
    >>> root.add_metadata(current=10.3, current_units='mA')
    >>> root.metadata
    {'voltage': 7.64, 'voltage_units': 'V', 'current': 10.3, 'current_units': 'mA'}
