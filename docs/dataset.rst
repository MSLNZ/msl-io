.. _msl-io-dataset:

=======
Dataset
=======
A :class:`~msl.io.dataset.Dataset` can be thought of as a file in your operating system and it
is contained within a :ref:`msl-io-group`.

A :class:`~msl.io.dataset.Dataset` is essentially a :class:`numpy.ndarray` with :ref:`msl-io-metadata`
and it can be accessed in read-only mode.

Depending on the :class:`numpy.dtype` that was used to create the underlying :class:`numpy.ndarray` for the
:class:`~msl.io.dataset.Dataset` the field names can be accessed as field attributes. For example, suppose
that `dset` is a :class:`~msl.io.dataset.Dataset` that has a :class:`numpy.ndarray` with :class:`numpy.dtype`
defined as ``[('x', float), ('y', float)]``.

You can access the data in `dset` as keys

.. code-block:: pycon

   >>> z = dset['x'] + dset['y']

or as attributes

.. code-block:: pycon

   >>> z = dset.x + dset.y

See :ref:`attribute-key-limitations` for more information.

To access the :class:`~msl.io.metadata.Metadata` for `dset`, use

.. code-block:: pycon

   >>> dset.metadata
