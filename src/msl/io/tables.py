"""
Read a data table from a file.
"""
import re

import numpy as np

from .base import Reader
from .dataset import Dataset
from .readers import ExcelReader
from .readers import GSheetsReader
from .utils import get_basename

_spreadsheet_top_left_regex = re.compile(r"^([A-Z]+)(\d+)$")
_spreadsheet_range_regex = re.compile(r"^[A-Z]+\d*:[A-Z]+\d*$")


extension_delimiter_map = {".csv": ","}
""":class:`dict`: The delimiter to use to separate columns in a table based on the file extension.

If the `delimiter` is not specified when calling the :func:`~msl.io.read_table` function then this
extension-delimiter map is used to determine the value of the `delimiter`. If the file extension
is not in the map then the value of the `delimiter` is :data:`None` (i.e., split columns by any
whitespace). 

Examples
--------
You can customize your own map by adding key-value pairs

.. code-block:: pycon

    >>> from msl.io import extension_delimiter_map
    >>> extension_delimiter_map['.txt'] = '\\t'

"""


def read_table_text(file, **kwargs):
    """Read a data table from a text-based file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read.
    **kwargs
        All keyword arguments are passed to :func:`~numpy.loadtxt`. If the
        `delimiter` is not specified and the `file` has ``csv`` as the file
        extension then the `delimiter` is automatically set to be ``','``.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included
        in the :class:`~msl.io.metadata.Metadata`.
    """
    if kwargs.get("unpack", False):
        raise ValueError('Cannot use the "unpack" option')

    if hasattr(file, "as_posix"):  # a pathlib.Path object
        file = str(file)

    if "delimiter" not in kwargs:
        extn = Reader.get_extension(file).lower()
        kwargs["delimiter"] = extension_delimiter_map.get(extn)

    if "skiprows" not in kwargs:
        kwargs["skiprows"] = 0
    kwargs["skiprows"] += 1  # Reader.get_lines is 1-based, np.loadtxt is 0-based

    first_line = Reader.get_lines(file, kwargs["skiprows"], kwargs["skiprows"])
    if not first_line:
        header, data = [], []
    else:
        header = first_line[0].split(kwargs["delimiter"])
        # Calling np.loadtxt (on Python 3.5, 3.6 and 3.7) on a file
        # on a mapped drive could raise an OSError. This occurred
        # when a local folder was shared and then mapped on the same
        # computer. Opening the file using open() and then passing
        # in the file handle to np.loadtxt is more universal
        if hasattr(file, "read"):  # already a file-like object
            data = np.loadtxt(file, **kwargs)
        else:
            with open(file, mode="rt") as fp:
                data = np.loadtxt(fp, **kwargs)
        use_cols = kwargs.get("usecols")
        if use_cols:
            if isinstance(use_cols, int):
                use_cols = [use_cols]
            header = [header[i] for i in use_cols]

    return Dataset(get_basename(file), None, True, data=data, header=np.asarray(header, dtype=str))


def read_table_excel(file, cells=None, sheet=None, as_datetime=True, dtype=None, **kwargs):
    """Read a data table from an Excel spreadsheet.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read.
    cells : :class:`str`, optional
        The cells to read. For example, ``C9`` will start at cell C9 and
        include all values until the end of the spreadsheet, ``A:C`` includes
        all rows in columns A, B and C, and, ``C9:G20`` includes
        values from only the specified cells. If not specified then returns
        all values from the specified `sheet`.
    sheet : :class:`str`, optional
        The name of the sheet to read the data from. If there is only one sheet
        in the workbook then you do not need to specify the name of the sheet.
    as_datetime : :class:`bool`, optional
        Whether dates should be returned as :class:`~datetime.datetime` or
        :class:`~datetime.date` objects. If :data:`False` then dates are returned
        as a :class:`str`.
    dtype : :class:`object`, optional
        If specified then it must be able to be converted to a :class:`~numpy.dtype` object.
    **kwargs
        All additional keyword arguments are passed to :func:`~xlrd.open_workbook`. Can use
        an `encoding` keyword argument as an alias for `encoding_override`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included
        in the :class:`~msl.io.metadata.Metadata`.
    """
    if hasattr(file, "as_posix"):  # a pathlib.Path object
        file = str(file)
    elif hasattr(file, "name"):  # a TextIOWrapper object
        file = file.name

    with ExcelReader(file, **kwargs) as excel:
        if cells is not None and not _spreadsheet_range_regex.match(cells):
            match = _spreadsheet_top_left_regex.match(cells)
            if not match:
                raise ValueError("Invalid cell {!r}".format(cells))
            name = sheet or excel.workbook.sheet_names()[0]
            s = excel.workbook.sheet_by_name(name)
            letters = excel.to_letters(s.ncols - 1)
            row = match.group(2)
            cells += ":{}{}".format(letters, row)
        table = excel.read(cell=cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def read_table_gsheets(file, cells=None, sheet=None, as_datetime=True, dtype=None, **kwargs):
    """Read a data table from a Google Sheets spreadsheet.

    .. attention::
       You must have already performed the instructions specified in
       :class:`.GDrive` and in :class:`.GSheets` to be able to use this function.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read. Can be the ID of a Google Sheets spreadsheet.
    cells : :class:`str`, optional
        The cells to read. For example, ``C9`` will start at cell C9 and
        include all values until the end of the spreadsheet, ``A:C`` includes
        all rows in columns A, B and C, and, ``C9:G20`` includes
        values from only the specified cells. If not specified then returns
        all values from the specified `sheet`.
    sheet : :class:`str`, optional
        The name of the sheet to read the data from. If there is only one sheet
        in the spreadsheet then you do not need to specify the name of the sheet.
    as_datetime : :class:`bool`, optional
        Whether dates should be returned as :class:`~datetime.datetime` or
        :class:`~datetime.date` objects. If :data:`False` then dates are returned
        as a :class:`str`.
    dtype : :class:`object`, optional
        If specified then it must be able to be converted to a :class:`~numpy.dtype` object.
    **kwargs
        All additional keyword arguments are passed to :class:`~msl.io.readers.gsheets.GSheetsReader`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included
        in the :class:`~msl.io.metadata.Metadata`.
    """
    if hasattr(file, "as_posix"):  # a pathlib.Path object
        file = str(file)
    elif hasattr(file, "name"):  # a TextIOWrapper object
        file = file.name

    with GSheetsReader(file, **kwargs) as sheets:
        if cells is not None and not _spreadsheet_range_regex.match(cells):
            if not _spreadsheet_top_left_regex.match(cells):
                raise ValueError("Invalid cell {!r}".format(cells))
            r, c = sheets.to_indices(cells)
            data = sheets.read(sheet=sheet, as_datetime=as_datetime)
            table = [row[c:] for row in data[r:]]
        else:
            table = sheets.read(cell=cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def _spreadsheet_to_dataset(table, file, dtype):
    if not table:
        header, data = [], []
    elif len(table) == 1:
        header, data = table[0], []
    elif len(table[0]) == 1:  # a single column
        header, data = table[0], [row[0] for row in table[1:]]
    else:
        header, data = table[0], table[1:]
        if len(data) == 1:  # a single row
            data = data[0]

    return Dataset(get_basename(file), None, True, data=data,
                   dtype=dtype, header=np.asarray(header, dtype=str))
