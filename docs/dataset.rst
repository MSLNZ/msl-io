.. _msl-io-dataset:

=======
Dataset
=======
A :class:`~msl.io.dataset.Dataset` is analogous to a file for an operating system and it
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
   >>> dset1 = root.create_dataset('dset1', data=[1, 2, 3], temperature=20.3)
   >>> dset2 = root.create_dataset('dset2', data=[4, 5, 6], temperature=21.7)

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

To access the :class:`~msl.io.metadata.Metadata` of a :class:`~msl.io.dataset.Dataset`,
you call the :obj:`~msl.io.vertex.Vertex.metadata` attribute

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

Depending on the :class:`numpy.dtype` that was used to create the underlying
:class:`numpy.ndarray` for the :class:`~msl.io.dataset.Dataset` the field names
can also be accessed as field attributes. For example, you can access the fields
in *my_dataset* as keys

.. code-block:: pycon

   >>> my_dataset['x']
   array([0.23, 1.86, 3.44, 5.91, 8.73])

or as attributes

.. code-block:: pycon

   >>> my_dataset.x
   array([0.23, 1.86, 3.44, 5.91, 8.73])

Note that the returned object is a :class:`numpy.ndarray` and therefore does not
contain any :class:`~msl.io.metadata.Metadata`.

See :ref:`attribute-key-limitations` for more information.

You can also chain multiple attribute calls together. For example, to get the
maximum *x* value in *my_dataset* you can use

.. code-block:: pycon

   >>> my_dataset.x.max()
   8.73

.. _msl-io-dataset-slicing:

Slicing and Indexing
--------------------
Slicing and indexing a :class:`~msl.io.dataset.Dataset` is a valid
operation, but returns a :class:`numpy.ndarray` which does not contain
any :ref:`msl-io-metadata`.

Consider *my_dataset* from above. One can slice it

.. code-block:: pycon

   >>> my_dataset[::2]
   array([(0.23, 1.27), (3.44, 2.91), (8.73, 0.74)],
          dtype=[('x', '<f8'), ('y', '<f8')])

or index it

.. code-block:: pycon

   >>> my_dataset[2]
   (3.44, 2.91)

Since a :class:`numpy.ndarray` is returned, you are responsible for keeping
track of the :ref:`msl-io-metadata` in slicing and indexing operations.
For example,

.. code-block:: pycon

   >>> my_subset = root.create_dataset('my_subset', data=my_dataset[::2], **my_dataset.metadata)
   >>> my_subset
   <Dataset '/my_subset' shape=(3,) dtype='|V16' (2 metadata)>
   >>> my_subset.data
   array([(0.23, 1.27), (3.44, 2.91), (8.73, 0.74)],
          dtype=[('x', '<f8'), ('y', '<f8')])
   >>> my_subset.metadata
   <Metadata '/my_subset' {'temperature': 20.13, 'humidity': 45.31}>

.. _msl-io-dataset-arithmetic:

Arithmetic Operations
---------------------
Arithmetic operations are valid with a :class:`~msl.io.dataset.Dataset`, however,
the returned object will be a :class:`numpy.ndarray` and therefore all
:class:`~msl.io.metadata.Metadata` of the :class:`~msl.io.dataset.Dataset`\s
that are involved in the operation are no longer included in the returned object.

For example, suppose you have two :class:`~msl.io.dataset.Dataset`\s that
contain the following information

.. code-block:: pycon

   >>> dset1
   <Dataset '/dset1' shape=(3,) dtype='<f8' (1 metadata)>
   >>> dset1.data
   array([1., 2., 3.])
   >>> dset1.metadata
   <Metadata '/dset1' {'temperature': 20.3}>

   >>> dset2
   <Dataset '/dset2' shape=(3,) dtype='<f8' (1 metadata)>
   >>> dset2.data
   array([4., 5., 6.])
   >>> dset2.metadata
   <Metadata '/dset2' {'temperature': 21.7}>

You can directly add the :class:`~msl.io.dataset.Dataset`\s, but the *temperature*
values in :class:`~msl.io.metadata.Metadata` are no longer included in the
returned object

.. code-block:: pycon

   >>> dset3 = dset1 + dset2
   >>> dset3
   array([5., 7., 9.])
   >>> dset3.metadata
   Traceback (most recent call last):
     File "<input>", line 1, in <module>
   AttributeError: 'numpy.ndarray' object has no attribute 'metadata'

You are responsible for keeping track of the :ref:`msl-io-metadata`
in arithmetic operations, for example,

.. code-block:: pycon

   >>> temperatures = {'t1': dset1.metadata.temperature, 't2': dset2.metadata.temperature}
   >>> dset3 = root.create_dataset('dset3', data=dset1+dset2, temperatures=temperatures)
   >>> dset3
   <Dataset '/dset3' shape=(3,) dtype='<f8' (1 metadata)>
   >>> dset3.data
   array([5., 7., 9.])
   >>> dset3.metadata
   <Metadata '/dset3' {'temperatures': {'t1': 20.3, 't2': 21.7}}>

.. _msl-io-dataset-logging:

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
