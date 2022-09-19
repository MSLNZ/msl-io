.. _msl-io-metadata:

========
Metadata
========
All :ref:`msl-io-group` and :ref:`msl-io-dataset` objects contain :class:`~msl.io.metadata.Metadata`. A
:class:`~msl.io.metadata.Metadata` object is a :class:`dict` that can be made read only and allows
for accessing the *keys* of the :class:`dict` as class attributes (see :ref:`attribute-key-limitations` for
more information).

For example, suppose that a file is read with the :class:`~msl.io.base.Root` :ref:`msl-io-group`
having the following :class:`~msl.io.metadata.Metadata`

.. invisible-code-block: pycon

   >>> SKIP_IF_PYTHON_LESS_THAN_36()
   >>> from msl.io import JSONWriter
   >>> root = JSONWriter()
   >>> root.add_metadata(voltage=1.2)
   >>> root.add_metadata(voltage_unit='V')
   >>> root.read_only = True

.. code-block:: pycon

   >>> root.metadata
   <Metadata '/' {'voltage': 1.2, 'voltage_unit': 'V'}>

A value can be accessed by specifying a *key*

.. code-block:: pycon

    >>> root.metadata['voltage']
    1.2

or as a class attribute

.. code-block:: pycon

    >>> root.metadata.voltage
    1.2

When a file is read, the :class:`~msl.io.base.Root` object is returned in read-only mode so
you cannot modify the metadata

.. code-block:: pycon

    >>> root.metadata.voltage = 7.64
    Traceback (most recent call last):
      ...
    ValueError: Cannot modify <Metadata '/' {'voltage': 1.2, 'voltage_unit': 'V'}>. It is accessed in read-only mode.

However, you can allow *root* to be modified by setting the :obj:`~msl.io.dictionary.Dictionary.read_only`
property to be :data:`False`

.. code-block:: pycon

    >>> root.metadata.read_only = False
    >>> root.metadata.voltage = 7.64
    >>> root.add_metadata(current=10.3, current_unit='mA')
    >>> root.metadata
    <Metadata '/' {'voltage': 7.64, 'voltage_unit': 'V', 'current': 10.3, 'current_unit': 'mA'}>
