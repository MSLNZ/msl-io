.. _msl-io-dataset:

=======
Dataset
=======
A :class:`~msl.io.dataset.Dataset` is analogous to a file for an operating system. and it
is contained within a :ref:`msl-io-group`.

A :class:`~msl.io.dataset.Dataset` is essentially a :class:`numpy.ndarray` with :ref:`msl-io-metadata`
and it can be accessed in read-only mode.

.. invisible-code-block: pycon

   >>> SKIP_IF_PYTHON_LESS_THAN_36()
   >>> from msl.io import JSONWriter
   >>> root = JSONWriter()
   >>> data = [(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)]
   >>> my_dataset = root.create_dataset('my_dataset', data=data, dtype=[('x', '<f8'), ('y', '<f8')])
   >>> my_dataset.add_metadata(temperature=20.13, humidity=45.31)

Since a :class:`~msl.io.dataset.Dataset` can be thought of as an :class:`numpy.ndarray` the attributes of
an :class:`numpy.ndarray` are also valid for a :class:`~msl.io.dataset.Dataset`. For example, suppose
`my_dataset` is a :class:`~msl.io.dataset.Dataset`

.. code-block:: pycon

   >>> my_dataset
   <Dataset '/my_dataset' shape=(5,) dtype='|V16' (2 metadata)>
   >>> my_dataset.data
   array([(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)],
         dtype=[('x', '<f8'), ('y', '<f8')])

You can get the :attr:`numpy.ndarray.shape` using

.. code-block:: pycon

   >>> my_dataset.shape
   (5,)

or convert the data in the :class:`~msl.io.dataset.Dataset` to a Python :class:`list`,
using :meth:`numpy.ndarray.tolist`

.. code-block:: pycon

   >>> my_dataset.tolist()
   [(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)]

To access the :class:`~msl.io.metadata.Metadata` of *my_dataset*, you access the
:obj:`~msl.io.vertex.Vertex.metadata` attribute

.. code-block:: pycon

   >>> my_dataset.metadata
   <Metadata '/my_dataset' {'temperature': 20.13, 'humidity': 45.31}>

You can access values of the :ref:`msl-io-metadata` as attributes

.. code-block:: pycon

   >>> my_dataset.metadata.temperature
   20.13

or as keys

.. code-block:: pycon

   >>> my_dataset.metadata['humidity']
   45.31

Depending on the :class:`numpy.dtype` that was used to create the underlying :class:`numpy.ndarray` for the
:class:`~msl.io.dataset.Dataset` the field names can be accessed as field attributes. For example, you can
access the fields as keys

.. code-block:: pycon

   >>> my_dataset['x'] + my_dataset['y']
   array([1.5 , 4.6 , 6.35, 7.74, 9.47])

or as attributes

.. code-block:: pycon

   >>> my_dataset.x + my_dataset.y
   array([1.5 , 4.6 , 6.35, 7.74, 9.47])

and you could get the maximum *y* value in the :class:`~msl.io.dataset.Dataset`,
using the :meth:`numpy.ndarray.max` method

.. code-block:: pycon

   >>> my_dataset.y.max()
   2.91

See :ref:`attribute-key-limitations` for more information.

Slicing the :class:`~msl.io.dataset.Dataset` is also a valid operation

.. code-block:: pycon

   >>> my_dataset[::2]
   array([(0.23, 1.27), (3.44, 2.91), (8.73, 0.74)],
          dtype=[('x', '<f8'), ('y', '<f8')])


A Dataset for Logging Records
-----------------------------
The :class:`~msl.io.dataset_logging.DatasetLogging` class is a custom :class:`~msl.io.dataset.Dataset`
that is also a :class:`~logging.Handler` which automatically appends :mod:`logging` records
to the :class:`~msl.io.dataset.Dataset`. See :meth:`~msl.io.group.Group.create_dataset_logging` for
more details.

When a file is :func:`~msl.io.read` it will load an object that was once a
:class:`~msl.io.dataset_logging.DatasetLogging` as a :class:`~msl.io.dataset.Dataset`.
If you want to convert the :class:`~msl.io.dataset.Dataset` to be a
:class:`~msl.io.dataset_logging.DatasetLogging` object, so that :mod:`logging` records are once
again appended to it, then call the :meth:`~msl.io.group.Group.require_dataset_logging` method
with the *name* argument equal to the value of *name* for the :class:`~msl.io.dataset.Dataset`.
