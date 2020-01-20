"""
A :class:`Dataset` is essentially a :class:`numpy.ndarray` with :class:`~msl.io.metadata.Metadata`.
"""
import numpy as np

from .vertex import Vertex


class Dataset(Vertex):

    def __init__(self, name, parent, is_read_only, shape=(0,), dtype=float, buffer=None,
                 offset=0, strides=None, order=None, data=None, **metadata):
        """A :class:`Dataset` is essentially a :class:`numpy.ndarray` with :class:`~msl.io.metadata.Metadata`.

        Do not instantiate directly. Create a new :class:`Dataset` using
        :meth:`~msl.io.group.Group.create_dataset`.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with this :class:`Dataset`.
        parent : :class:`~msl.io.group.Group`
            The parent :class:`~msl.io.group.Group` to the :class:`Dataset`.
        is_read_only : :class:`bool`
            Whether the :class:`Dataset` is to be accessed in read-only mode.
        shape
            See :class:`numpy.ndarray`
        dtype
            See :class:`numpy.ndarray`
        buffer
            See :class:`numpy.ndarray`
        offset
            See :class:`numpy.ndarray`
        strides
            See :class:`numpy.ndarray`
        order
            See :class:`numpy.ndarray`
        data
            If not :data:`None` then it must be either a :class:`numpy.ndarray` or
            an array-like object which will be passed to :func:`numpy.asarray`,
            as well as `dtype` and `order`, to be used as the underlying data.
        **metadata
            All other key-value pairs will be used as
            :class:`~msl.io.metadata.Metadata` for this :class:`Dataset`.
        """
        super(Dataset, self).__init__(name, parent, is_read_only, **metadata)

        if data is None:
            self._data = np.ndarray(
                shape, dtype=dtype, buffer=buffer, offset=offset, strides=strides, order=order
            )
        else:
            if isinstance(data, np.ndarray):
                self._data = data
            else:
                self._data = np.asarray(data, dtype=dtype, order=order)

        self.is_read_only = is_read_only

    def __repr__(self):
        return '<{} {!r} shape={} dtype={} ({} metadata)>'\
            .format(self.__class__.__name__, self._name, self._data.shape, self._data.dtype.str, len(self.metadata))

    def __str__(self):
        return repr(self._data)

    @property
    def is_read_only(self):
        """:class:`bool`: Whether this :class:`Dataset` is in read-only mode.

        This is equivalent to setting the ``WRITEABLE`` property in :meth:`numpy.ndarray.setflags`.
        """
        return not self._data.flags.writeable

    @is_read_only.setter
    def is_read_only(self, value):
        val = bool(value)
        self._metadata.is_read_only = val
        self._data.setflags(write=not val)

    def copy(self, is_read_only=None):
        """Create a copy of this :class:`Dataset`.

        Parameters
        ----------
        is_read_only : :class:`bool`, optional
            Whether the copy should be created in read-only mode. If :data:`None` then
            creates a copy using the mode for the :class:`Dataset` that is being copied.

        Returns
        -------
        :class:`Dataset`
            A copy of this :class:`Dataset`.
        """
        return Dataset(
            self._name,
            self._parent,
            self._is_read_only if is_read_only is None else is_read_only,
            data=self._data.copy(),
            **self._metadata.copy()
        )

    @property
    def data(self):
        """:class:`numpy.ndarray`: The data of the :class:`Dataset`.

        .. note::
           You do not have to call this attribute to get access to the
           :class:`numpy.ndarray`. You can directly call the
           :class:`numpy.ndarray` attribute from the :class:`Dataset`
           object.

           For example,

           .. code-block:: pycon

              >>> from msl.io import JSONWriter
              >>> root = JSONWriter()
              >>> dset = root.create_dataset('my_data', data=[[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]])
              >>> dset.size
              12
              >>> dset.tolist()
              [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0], [6.0, 7.0, 8.0], [9.0, 10.0, 11.0]]
              >>> dset.mean(axis=1)
              array([ 1.,  4.,  7., 10.])
        """
        return self._data

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, item, value):
        self._data[item] = value

    def __getattr__(self, item):
        try:
            return self._data[item]
        except (IndexError, ValueError):
            return getattr(self._data, item)

    def __len__(self):
        # if the ndarray is a scalar then the following exception is raised
        #   TypeError: len() of unsized object
        try:
            return len(self._data)
        except TypeError:
            return self._data.size

    def __iter__(self):
        return iter(self._data)
