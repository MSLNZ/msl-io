"""
Read a data table from a file.
"""
import os
import re

import xlrd
import numpy as np

from . import (
    Reader,
    ExcelReader,
    GDrive,
    GSheets,
)
from .dataset import Dataset
from .utils import get_basename

_excel_range_regex = re.compile(r'([a-zA-Z]+)(\d+):([a-zA-Z]+)(\d+)')
_google_file_id_regex = re.compile(r'^1[a-zA-Z0-9_-]{43}$')

extension_delimiter_map = {'.csv': ','}
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
    if kwargs.get('unpack', False):
        raise ValueError('Cannot use the "unpack" option')

    if 'delimiter' not in kwargs:
        extn = Reader.get_extension(file).lower()
        kwargs['delimiter'] = extension_delimiter_map.get(extn)

    if 'skiprows' not in kwargs:
        kwargs['skiprows'] = 1

    first_line = Reader.get_lines(file, kwargs['skiprows'], kwargs['skiprows'])
    if not first_line:
        header, data = [], []
    else:
        header = first_line[0].split(kwargs['delimiter'])
        data = np.loadtxt(file, **kwargs)
        use_cols = kwargs.get('usecols')
        if use_cols:
            if isinstance(use_cols, int):
                use_cols = [use_cols]
            header = [header[i] for i in use_cols]

    return Dataset(get_basename(file), None, True, data=data, header=np.asarray(header, dtype=str))


def read_table_excel(file, cell=None, sheet=None, as_datetime=True, dtype=None, **kwargs):
    """Read a data table from an Excel spreadsheet.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The file to read.
    cell : :class:`str`, optional
        The cells to read (for example, ``'C9:G20'``). If not specified then reads all data
        in the specified `sheet`.
    sheet : :class:`str`, optional
        The name of the sheet to read the data from. If there is only one sheet
        in the workbook then you do not need to specify the name of the sheet.
    as_datetime : :class:`bool`, optional
        Whether dates should be returned as :class:`~datetime.datetime` objects.
        If :data:`False` then dates are returned as an ISO-8601 :class:`str`.
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
    if hasattr(file, 'name'):  # a TextIOWrapper object
        file = file.name

    match = None
    if cell is not None:
        match = _excel_range_regex.match(str(cell).replace('$', ''))
        if not match:
            raise ValueError('You must specify a valid cell range, for example, "C3:M25"')

    excel = ExcelReader(file, **kwargs)
    table = excel.read(cell=cell, sheet=sheet, as_datetime=as_datetime)
    if not table:
        header, data = [], []
    else:
        # determine the range of rows and columns that were requested
        # to make the result consistent with the way read_table_text would return the table
        if match:
            col1, row1, col2, row2 = match.groups()
        else:
            if excel.workbook.nsheets == 1:
                sheet = excel.workbook.sheet_by_index(0)
            else:
                sheet = excel.workbook.sheet_by_name(sheet)
            row1, col1 = 1, 1
            row2, col2 = sheet.nrows, sheet.ncols

        if row1 == row2:
            header, data = table, []
        elif col1 == col2:
            header, data = [table[0]], table[1:]
        else:
            header, data = table[0], table[1:]
            if len(data) == 1:  # a row vector
                data = data[0]

    excel.close()
    return Dataset(get_basename(file), None, True, data=data, dtype=dtype, header=np.asarray(header, dtype=str))


def read_table_gsheets(file, cell=None, sheet=None, as_datetime=True, dtype=None, **kwargs):
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
    cell : :class:`str`, optional
        The cells to read (for example, ``'C9'`` means start from cell C9 and
        ``'C9:G20'`` means to use only the specified cells). If not
        specified then reads all data in the specified `sheet`.
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
        All additional keyword arguments are passed to :func:`msl.io.google_api.GSheets`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is included
        in the :class:`~msl.io.metadata.Metadata`.
    """
    if hasattr(file, 'name'):  # a TextIOWrapper object
        file = file.name

    # get the spreadsheet ID
    path, ext = os.path.splitext(file)
    folders, _ = os.path.split(path)
    if ext or folders or not _google_file_id_regex.match(path):
        spreadsheet_id = GDrive(**kwargs).file_id(path, mime_type=GSheets.MIME_TYPE)
    else:
        spreadsheet_id = path

    # build the table
    table = []
    for row in GSheets(**kwargs).cells(spreadsheet_id, sheet=sheet):
        row_values = []
        for item in row:
            if item.type == 'DATE':
                value = GSheets.to_datetime(item.value).date() if as_datetime else item.formatted
            elif item.type == 'DATE_TIME':
                value = GSheets.to_datetime(item.value) if as_datetime else item.formatted
            else:
                value = item.value
            row_values.append(value)
        table.append(tuple(row_values))

    # slice the table based on the cell range
    if cell is not None:
        cells = str(cell).upper().replace('$', '').split(':')
        if len(cells) == 1:
            row, col = xlrd.xlsx.cell_name_to_rowx_colx(cells[0])
            row_slice = slice(row, None)
            col_slice = slice(col, None)
        else:
            start_row, start_col = xlrd.xlsx.cell_name_to_rowx_colx(cells[0])
            end_row, end_col = xlrd.xlsx.cell_name_to_rowx_colx(cells[1])
            row_slice = slice(start_row, end_row+1)
            col_slice = slice(start_col, end_col+1)
        table = [row[col_slice] for row in table[row_slice]]

    # determine the header and the data for the Dataset
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

    return Dataset(get_basename(file), None, True, data=data, dtype=dtype, header=np.asarray(header, dtype=str))
