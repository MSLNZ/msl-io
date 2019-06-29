"""
Writer for the HDF5_ file format.

.. attention::
   requires that the H5py_ package is installed.

.. _HDF5: https://www.hdfgroup.org/
.. _H5py: https://www.h5py.org/
"""
import sys

try:
    import h5py
except ImportError:
    h5py = None

from .. import Writer
from ..metadata import Metadata
from ..base_io import Root

if sys.version_info.major > 2:
    unicode = str


class HDF5Writer(Writer):

    def write(self, url=None, root=None, **kwargs):
        """Write to a HDF5_ file.

        Parameters
        ----------
        url : :class:`str`, optional
            The name of the file to write to. If :data:`None` then uses the value of
            `url` that was specified when :class:`HDF5Writer` was created.
        root : :class:`~msl.io.base_io.Root`, optional
            Write `root` in HDF5_ format. If :data:`None` then write the
            :class:`~msl.io.group.Group`\\s and :class:`~msl.io.dataset.Dataset`\\s
            in this :class:`HDF5Writer`.
        **kwargs
            All key-value pairs are passed to :class:`File`.
        """
        if h5py is None:
            raise ImportError('You must install h5py to write HDF5 files.\nRun: pip install h5py')

        url = self.url if url is None else url
        if not url:
            raise ValueError('You must specify a url to write the file to')

        if root is None:
            root = self
        elif not isinstance(root, Root):
            raise TypeError('the root parameter must be a Root object')

        if 'mode' not in kwargs:
            kwargs['mode'] = 'x'  # Create file, fail if exists

        def meta_to_dict(metadata):
            return dict((k, meta_to_dict(v) if isinstance(v, Metadata) else v)
                        for k, v in metadata.items())

        h5 = h5py.File(url, **kwargs)
        h5.attrs.update(**meta_to_dict(root.metadata))
        for name, vertex in root.items():
            if self.is_dataset(vertex):
                data = vertex.data
                if vertex.dtype.names is not None:
                    convert, dtype = False, []
                    for n in vertex.dtype.names:
                        typ = vertex.dtype.fields[n][0]
                        if isinstance(typ, object) and isinstance(vertex[n].item(0), unicode):
                            # HDF5 variable-length string
                            dtype.append((n, h5py.special_dtype(vlen=str)))
                            convert = True
                        else:
                            dtype.append((n, typ))
                    if convert:
                        data = vertex.data.astype(dtype=dtype)
                obj = h5.create_dataset(name, data=data)
            else:
                obj = h5.create_group(name)
            obj.attrs.update(**meta_to_dict(vertex.metadata))
        h5.close()
