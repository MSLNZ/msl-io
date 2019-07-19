"""
Read and write MSL data files.
"""
import re
import os
import importlib
from collections import namedtuple

from .utils import search
from .register import (
    register,
    _readers,
)
from .base_io import (
    Reader,
    Writer,
)
from .writers import (
    JSONWriter,
    HDF5Writer,
)

__author__ = 'Measurement Standards Laboratory of New Zealand'
__copyright__ = '\xa9 2018 - 2019, ' + __author__
__version__ = '0.1.0.dev0'

_v = re.search(r'(\d+)\.(\d+)\.(\d+)[.-]?(.*)', __version__).groups()

version_info = namedtuple('version_info', 'major minor micro releaselevel')(int(_v[0]), int(_v[1]), int(_v[2]), _v[3])
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro, releaselevel) tuple."""

# import all Reader classes that are in the "./readers" directory
for module in os.listdir(os.path.dirname(__file__) + '/readers'):
    if module.endswith('.py') and not module.startswith('_'):
        importlib.import_module('msl.io.readers.'+module[:-3])


def read(url, **kwargs):
    """Factory function for reading a data file.

    Parameters
    ----------
    url : :class:`str`
        The path to the file to read.
    **kwargs
        Keyword arguments that are passed to the :meth:`~msl.io.base_io.Reader.can_read`
        and :meth:`~msl.io.base_io.Reader.read` methods.

    Returns
    -------
    :class:`~msl.io.base_io.Reader`
        The data from the file.

    Raises
    ------
    IOError
        If the file does not exist or if no :class:`~msl.io.base_io.Reader` exists
        to be able to read the specified file.
    """
    if not os.path.isfile(url):
        raise IOError('File does not exist {!r}'.format(url))

    for rdr in _readers:
        try:
            can_read = rdr.can_read(url, **kwargs)
        except:
            continue

        if can_read:
            root = rdr(url)
            root.read(**kwargs)
            root.is_read_only = True
            return root

    raise IOError('No Reader exists to read {!r}'.format(url))
