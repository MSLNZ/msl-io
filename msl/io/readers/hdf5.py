"""
Reader for the HDF5_ file format.

.. attention::
   This Reader loads the entire HDF5_ file in memory. If you need to use any of
   the more advanced features of a HDF5_ file then it is best to directly load
   the file using H5py_.

.. _HDF5: https://www.hdfgroup.org/
.. _H5py: https://www.h5py.org/
"""
import os

try:
    import h5py
except ImportError:
    h5py = None

from .. import (
    register,
    Reader,
)


@register
class HDF5Reader(Reader):
    """Reader for the HDF5_ file format."""

    @staticmethod
    def can_read(file, **kwargs):
        """The HDF5_ file format has a standard signature_.

        The first 8 bytes are ``\\x89HDF\\r\\n\\x1a\\n``.

        .. _signature: https://support.hdfgroup.org/HDF5/doc/H5.format.html#Superblock
        """
        return Reader.get_bytes(file, 8) == b'\x89HDF\r\n\x1a\n'

    def read(self, **kwargs):
        """Reads the HDF5_ file.

        Parameters
        ----------
        **kwargs
            All key-value pairs are passed to :class:`~h5py.File`.
        """
        if h5py is None:
            raise ImportError('You must install h5py to read HDF5 files.\nRun: pip install h5py')

        def convert(name, obj):
            head, tail = os.path.split(name)
            s = self['/' + head] if head else self
            if isinstance(obj, h5py.Dataset):
                s.create_dataset(tail, data=obj[:], **obj.attrs)
            elif isinstance(obj, h5py.Group):
                s.create_group(tail, **obj.attrs)
            else:
                assert False, 'Unhandled HDF5Reader object {}'.format(obj)

        h5 = h5py.File(self.file, mode='r', **kwargs)
        self.add_metadata(**h5.attrs)
        h5.visititems(convert)
        h5.close()
