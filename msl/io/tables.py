"""
Read tabular data from a file.
"""
import re
import os

import numpy as np

from . import (
    Reader,
    ExcelReader,
)
from .dataset import Dataset

_excel_range_regex = re.compile(r'([a-zA-Z]+)(\d+):([a-zA-Z]+)(\d+)')


def read_table_text(url, **kwargs):
    """Read tabular data from a text-based file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All values in a column are of the same data type.

    Parameters
    ----------
    url : :class:`str`
        The path to the file to read.
    **kwargs
        All keyword arguments are passed to :func:`numpy.loadtxt`. The
        `delimiter` is automatically set to be ``','`` for CSV files.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is defined as metadata.
    """
    if kwargs.get('unpack', False):
        raise ValueError('Cannot use the "unpack" option')

    if 'delimiter' not in kwargs:
        extn = Reader.get_extension(url)
        delimiter_map = {'.csv': ','}
        kwargs['delimiter'] = delimiter_map.get(extn)

    if 'skiprows' not in kwargs:
        kwargs['skiprows'] = 1

    first_line = Reader.get_lines(url, 1, remove_empty_lines=True)
    if not first_line:
        header = np.array([], dtype=str)
        data = np.array([])
    else:
        header = first_line[0].split(kwargs['delimiter'])
        data = np.loadtxt(url, **kwargs)
        if 'usecols' in kwargs:
            if isinstance(kwargs['usecols'], int):
                kwargs['usecols'] = [kwargs['usecols']]
            header = [header[i] for i in kwargs['usecols']]

    return Dataset(os.path.basename(url), None, True, data=data, header=np.asarray(header))


def read_table_excel(url, cell=None, sheet=None, as_datetime=True, dtype=None, **kwargs):
    """Read tabular data from an Excel spreadsheet.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All values in a column are of the same data type.

    Parameters
    ----------
    url : :class:`str`
        The path to the file to read.
    cell : :class:`str`, optional
        The cells to read (for example, `'C9:G20'``). If not specified then reads all data
        in the specified `sheet`.
    sheet : :class:`str`, optional
        The name of the sheet to read the data from. If there is only one sheet
        in the workbook then you do not need to specify the name of the sheet.
    as_datetime : :class:`bool`, optional
        Whether dates should be returned as :class:`~datetime.datetime` objects.
        If :data:`False` then dates are returned as an ISO-8601 :class:`str`.
    dtype : :class:`object`, optional
        If specified then it must be able to be converted to a :class:`numpy.dtype` object.
    **kwargs
        All keyword arguments are passed to :func:`xlrd.open_workbook`.

    Returns
    -------
    :class:`~msl.io.dataset.Dataset`
        The table as a :class:`~msl.io.dataset.Dataset`. The header is defined as metadata.
    """
    match = None
    if cell is not None:
        match = _excel_range_regex.match(str(cell).replace('$', ''))
        if not match:
            raise ValueError('You must specify a range of cells, for example, "C3:M25"')

    excel = ExcelReader(url, **kwargs)
    table = excel.read(cell=cell, sheet=sheet, as_datetime=as_datetime)
    if not table:
        header = np.array([], dtype=str)
        data = np.array([])
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
            header = np.asarray(table, dtype=str)
            data = np.asarray(table, dtype=dtype)
        elif col1 == col2:
            header = np.asarray([table[0]], dtype=str)
            if len(table) == 1:
                data = np.asarray([table[0]], dtype=dtype)
            else:
                data = np.asarray(table[1:], dtype=dtype).flatten()
        else:
            header = np.asarray(table[0], dtype=str)
            data = np.asarray(table[1:], dtype=dtype)
            if len(data) == 1:  # a row vector
                data = np.asarray(data[0], dtype=dtype)

    excel.close()
    return Dataset(os.path.basename(url), None, True, data=data, header=header)
