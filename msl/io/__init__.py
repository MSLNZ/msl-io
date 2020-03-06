"""
Read and write MSL data files.
"""
import re
import os
import importlib
from collections import namedtuple

from .utils import (
    search,
    send_email,
    register,
    git_revision,
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
from .base_io import Root
from .readers.excel import ExcelReader
from .tables import (
    read_table_text,
    read_table_excel,
    extension_delimiter_map,
)

__author__ = 'Measurement Standards Laboratory of New Zealand'
__copyright__ = '\xa9 2018 - 2020, ' + __author__
__version__ = '0.1.0.dev0'

_v = re.search(r'(\d+)\.(\d+)\.(\d+)[.-]?(.*)', __version__).groups()

version_info = namedtuple('version_info', 'major minor micro releaselevel')(int(_v[0]), int(_v[1]), int(_v[2]), _v[3])
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro, releaselevel) tuple."""

# import all Reader classes that are in the "./readers" directory
for module in os.listdir(os.path.dirname(__file__) + '/readers'):
    if module.endswith('.py') and not module.startswith('_'):
        importlib.import_module('msl.io.readers.'+module[:-3])


def read(file, **kwargs):
    """Read a file that has a :ref:`Reader <io-readers>` implemented.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read. For example, it could be a :class:`str` representing
        a file system path or a stream.
    **kwargs
        Keyword arguments that are passed to the :meth:`Reader.can_read() <msl.io.base_io.Reader.can_read>`
        and :meth:`Reader.read() <msl.io.base_io.Reader.read>` methods.

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
    if not hasattr(file, 'read') and not os.path.isfile(file):
        raise IOError('File does not exist {!r}'.format(file))

    for rdr in _readers:
        try:
            can_read = rdr.can_read(file, **kwargs)
        except:
            continue

        if can_read:
            root = rdr(file)
            root.read(**kwargs)
            root.is_read_only = True
            return root

    raise IOError('No Reader exists to read {!r}'.format(file))


def read_table(file, **kwargs):
    """Read tabular data from a file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read. For example, it could be a :class:`str` representing
        a file system path or a stream.
    **kwargs
        If the file is an Excel spreadsheet then the keyword arguments are passed to
        :func:`~msl.io.tables.read_table_excel` otherwise all keyword arguments are passed
        to :func:`~msl.io.tables.read_table_text`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included as metadata.
    """
    extn = Reader.get_extension(file).lower()
    if extn.startswith('.xls'):
        if hasattr(file, 'name'):  # a TextIOWrapper object that was created by calling open()
            file = file.name
        return read_table_excel(file, **kwargs)
    else:
        return read_table_text(file, **kwargs)
