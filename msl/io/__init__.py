"""
Read and write data files.
"""
import re
from collections import namedtuple

from .base import Reader
from .base import Root
from .base import Writer
from .google_api import GCellType
from .google_api import GDateTimeOption
from .google_api import GDrive
from .google_api import GMail
from .google_api import GSheets
from .google_api import GValueOption
from .readers import ExcelReader
from .readers import GSheetsReader
from .tables import extension_delimiter_map
from .tables import read_table_excel
from .tables import read_table_gsheets
from .tables import read_table_text
from .utils import _readers
from .utils import checksum
from .utils import copy
from .utils import git_head
from .utils import is_admin
from .utils import is_dir_accessible
from .utils import is_file_readable
from .utils import logger
from .utils import register
from .utils import remove_write_permissions
from .utils import run_as_admin
from .utils import search
from .utils import send_email
from .writers import HDF5Writer
from .writers import JSONWriter

__author__ = 'Measurement Standards Laboratory of New Zealand'
__copyright__ = '\xa9 2018 - 2022, ' + __author__
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
        All keyword arguments are passed to the
        :meth:`Reader.can_read() <msl.io.base.Reader.can_read>`
        and :meth:`Reader.read() <msl.io.base.Reader.read>` methods.

    Returns
    -------
    :class:`~msl.io.base.Reader`
        The data from the file.

    Raises
    ------
    OSError
        If no :class:`~msl.io.base.Reader` exists to be able to read
        the specified file.
    """
    if hasattr(file, 'as_posix'):  # a pathlib.Path object
        file = str(file)

    if hasattr(file, 'read') or is_file_readable(file, strict=True):
        logger.debug('finding Reader for %r', file)
        for r in _readers:
            logger.debug('checking %s', r.__name__)
            try:
                can_read = r.can_read(file, **kwargs)
            except Exception as e:
                logger.debug('%s: %s [%s]', e.__class__.__name__, e, r.__name__)
                continue

            if can_read:
                logger.debug('reading file with %s', r.__name__)
                root = r(file)
                root.read(**kwargs)
                root.read_only = True
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
        Otherwise, all keyword arguments are passed to :func:`~msl.io.tables.read_table_text`.

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
