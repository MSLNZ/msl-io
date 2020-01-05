.. _msl-io-dataset:

=======
Dataset
=======
A :class:`~msl.io.dataset.Dataset` can be thought of as a file on your operating system and it
is contained within a :ref:`msl-io-group`.

A :class:`~msl.io.dataset.Dataset` is essentially an :class:`~numpy.ndarray` with :ref:`msl-io-metadata`
and it can be accessed in read-only mode.

Since a :class:`~msl.io.dataset.Dataset` can be thought of as an :class:`~numpy.ndarray` the attributes of
an :class:`~numpy.ndarray` are also valid for a :class:`~msl.io.dataset.Dataset`. For example, suppose
`my_dataset` is a :class:`~msl.io.dataset.Dataset` then you can get the shape using

.. code-block:: pycon

   >>> my_dataset.shape

or, convert the :class:`~msl.io.dataset.Dataset` to a Python :class:`list`, using :meth:`~numpy.ndarray.tolist`

.. code-block:: pycon

   >>> my_dataset.tolist()

or, get the maximum value in the :class:`~msl.io.dataset.Dataset`, using :meth:`~numpy.ndarray.max`

.. code-block:: pycon

   >>> my_dataset.max()

To access the :class:`~msl.io.metadata.Metadata` for `my_dataset`, use

.. code-block:: pycon

   >>> my_dataset.metadata

Depending on the :class:`~numpy.dtype` that was used to create the underlying :class:`~numpy.ndarray` for the
:class:`~msl.io.dataset.Dataset` the field names can be accessed as field attributes. For example, suppose
that `dset` is a :class:`~msl.io.dataset.Dataset` that has a :class:`~numpy.dtype` equal to
``[('x', float), ('y', float)]``.

You can access the fields in `dset` as keys

.. code-block:: pycon

   >>> z = dset['x'] + dset['y']

or as attributes

.. code-block:: pycon

   >>> z = dset.x + dset.y

See :ref:`attribute-key-limitations` for more information.

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
