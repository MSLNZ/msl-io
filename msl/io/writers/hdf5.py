"""
Writer for the HDF5_ file format.

.. attention::
   requires that the h5py_ package is installed.

.. _HDF5: https://www.hdfgroup.org/
.. _h5py: https://www.h5py.org/
"""
import numpy as np
try:
    import h5py
except ImportError:
    h5py = None

from .. import Writer
from ..metadata import Metadata
from ..base_io import Root
from ..constants import IS_PYTHON2

if not IS_PYTHON2:
    unicode = str


class HDF5Writer(Writer):
    """Create a HDF5_ writer."""

    def write(self, url=None, root=None, **kwargs):
        """Write to a HDF5_ file.

        Parameters
        ----------
        url : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The file to write the `root` to. If :data:`None` then uses the value of
            `url` that was specified when :class:`HDF5Writer` was instantiated.
        root : :class:`~msl.io.base_io.Root`, optional
            Write `root` in HDF5_ format. If :data:`None` then write the
            :class:`~msl.io.group.Group`\\s and :class:`~msl.io.dataset.Dataset`\\s
            in this :class:`HDF5Writer`.
        **kwargs
            All key-value pairs are passed to :class:`File`.
        """
        if h5py is None:
            raise ImportError('You must install h5py to write HDF5 files.\nRun: pip install h5py')

        if url is None:
            url = self.url
        if not url:
            raise ValueError('You must specify a url to write the file to')

        if root is None:
            root = self
        elif not isinstance(root, Root):
            raise TypeError('The root parameter must be a Root object')

        if 'mode' not in kwargs:
            kwargs['mode'] = 'x'  # Create file, fail if exists

        def check_ndarray_dtype(obj):
            if not isinstance(obj, np.ndarray):
                return obj

            # h5py variable-length string
            vstr = h5py.special_dtype(vlen=str)

            if obj.dtype.names is not None:
                convert, dtype = False, []
                for n in obj.dtype.names:
                    typ = obj.dtype.fields[n][0]
                    if isinstance(obj[n].item(0), (unicode, str)):
                        dtype.append((n, vstr))
                        convert = True
                    else:
                        dtype.append((n, typ))
                if convert:
                    return obj.astype(dtype=dtype)
                return obj
            elif obj.dtype.str == '|U':
                return obj.astype(dtype=vstr)
            elif obj.dtype.str == '|O':
                has_complex = False
                for item in obj.flat:
                    if isinstance(item, (unicode, str)):
                        return obj.astype(dtype=vstr)
                    elif isinstance(item, np.complexfloating):
                        has_complex = True
                    elif item is None:
                        return obj  # let h5py raise the error that HDF5 does not support NULL
                if has_complex:
                    return obj.astype(dtype=complex)
                return obj.astype(dtype=float)
            else:
                return obj

        def meta_to_dict(metadata):
            return dict((k, meta_to_dict(v) if isinstance(v, Metadata) else check_ndarray_dtype(v))
                        for k, v in metadata.items())

        with h5py.File(url, **kwargs) as h5:
            h5.attrs.update(**meta_to_dict(root.metadata))
            for name, value in root.items():
                if self.is_dataset(value):
                    try:
                        vertex = h5.create_dataset(name, data=value.data)
                    except TypeError:
                        vertex = h5.create_dataset(name, data=check_ndarray_dtype(value.data))
                else:
                    vertex = h5.create_group(name)
                vertex.attrs.update(**meta_to_dict(value.metadata))
