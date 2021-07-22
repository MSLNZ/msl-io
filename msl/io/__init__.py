"""
Read and write data files.
"""
import re
from collections import namedtuple

from .utils import (
    _readers,
    checksum,
    copy,
    git_revision,
    is_dir_accessible,
    is_file_readable,
    register,
    remove_write_permissions,
    search,
    send_email,
)
from .base_io import (
    Root,
    Reader,
    Writer,
)
from .writers import (
    JSONWriter,
    HDF5Writer,
)
from .google_api import (
    GDrive,
    GSheets,
    GValueOption,
    GDateTimeOption,
    GCellType,
)
from .readers import (
    ExcelReader,
    GSheetsReader,
)
from .tables import (
    read_table_text,
    read_table_excel,
    read_table_gsheets,
    extension_delimiter_map,
)

__author__ = 'Measurement Standards Laboratory of New Zealand'
__copyright__ = '\xa9 2018 - 2021, ' + __author__
__version__ = '0.1.0.dev0'

_v = re.search(r'(\d+)\.(\d+)\.(\d+)[.-]?(.*)', __version__).groups()

version_info = namedtuple('version_info', 'major minor micro releaselevel')(int(_v[0]), int(_v[1]), int(_v[2]), _v[3])
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro, releaselevel) tuple."""


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
    OSError
        If no :class:`~msl.io.base_io.Reader` exists to be able to read
        the specified file.
    """
    if hasattr(file, 'as_posix'):  # a pathlib.Path object
        file = str(file)

    if hasattr(file, 'read') or is_file_readable(file, strict=True):
        pass

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

    raise OSError('No Reader exists to read {!r}'.format(file))


def read_table(file, **kwargs):
    """Read data in a table format from a file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read. For example, it could be a :class:`str` representing
        a file system path or a stream. If `file` is a Google Sheets spreadsheet
        then `file` must end with ``.gsheet`` even if the ID of the spreadsheet
        is specified.
    **kwargs
        If the file is an Excel spreadsheet then the keyword arguments are passed to
        :func:`~msl.io.tables.read_table_excel`. If a Google Sheets spreadsheet then
        the keyword arguments are passed to :func:`~msl.io.tables.read_table_gsheets`.
        Otherwise all keyword arguments are passed to :func:`~msl.io.tables.read_table_text`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included as metadata.
    """
    extn = Reader.get_extension(file).lower()
    if extn.startswith('.xls'):
        return read_table_excel(file, **kwargs)
    elif extn == '.gsheet':
        if hasattr(file, 'as_posix'):  # a pathlib.Path object
            file = str(file)
        elif hasattr(file, 'name'):  # a TextIOWrapper object
            file = file.name
        return read_table_gsheets(file[:-7], **kwargs)  # ignore the extension
    else:
        return read_table_text(file, **kwargs)
