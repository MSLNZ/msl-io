"""
Reader for Excel spreadsheets (.xls and .xlsx).
"""
from datetime import datetime

import xlrd

# Do not register this Reader because the information in an Excel file is unstructured
# and one cannot generalize how to create a Root.


class ExcelReader(object):

    def __init__(self, url, **kwargs):
        """Reader for Excel spreadsheets (.xls and .xlsx).

        This class simply provides a convenience for reading information
        from Excel spreadsheets. It is not a registered :class:`~msl.io.base_io.Reader`.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        **kwargs
            All keyword arguments are passed to :func:`~xlrd.open_workbook`.
        """

        # change the default on_demand value
        if 'on_demand' not in kwargs:
            kwargs['on_demand'] = True

        self._url = url
        self._workbook = xlrd.open_workbook(url, **kwargs)

    @property
    def url(self):
        """:class:`str`: The location of the file on a local hard drive or on a network."""
        return self._url

    @property
    def workbook(self):
        """:class:`~xlrd.book.Book`: The workbook instance."""
        return self._workbook

    def read(self, cell=None, sheet=None, as_datetime=True):
        """Read information from an Excel spreadsheet.

        Parameters
        ----------
        cell : :class:`str`, optional
            The cell(s) to read. For example, ``'C9'`` will return a single value
            and ``'C9:G20'`` will return all values in the specified range. If not specified
            then returns all information in the specified `sheet`.
        sheet : :class:`str`, optional
            The name of the sheet to read the information from. If there is only one sheet
            in the workbook then you do not need to specify the name of the sheet.
        as_datetime : :class:`bool`, optional
            Whether dates should be returned as :class:`~datetime.datetime` objects.
            If :data:`False` then dates are returned as an ISO-8601 :class:`str`.

        Returns
        -------
        The information in the requested cell(s).
        """
        if sheet is None:
            names = self._workbook.sheet_names()
            if len(names) > 1:
                raise IOError('{!r} contains the following sheets:\n  {}\n'
                              'You must specify the name of the sheet to read'
                              .format(self._url, ', '.join(names)))
            else:
                sheet_name = names[0]
        else:
            sheet_name = sheet

        try:
            sheet = self._workbook.sheet_by_name(sheet_name)
        except xlrd.XLRDError:
            # TODO want to raise IOError without nested exceptions
            #  Can "raise from None" when dropping Python 2 support
            sheet = None

        if sheet is None:
            raise IOError('There is no sheet named {!r} in {!r}'.format(sheet_name, self._url))

        if cell is None:
            start_row, end_row = 0, sheet.nrows - 1
            start_col, end_col = 0, sheet.ncols - 1
            return self._get_cell_range(sheet, start_row, end_row, start_col, end_col, as_datetime)

        cells = str(cell).upper().replace('$', '').split(':')
        if len(cells) == 1:
            r, c = xlrd.xlsx.cell_name_to_rowx_colx(cells[0])
            return self._get_cell(sheet, r, c, as_datetime)
        else:
            start_row, start_col = xlrd.xlsx.cell_name_to_rowx_colx(cells[0])
            end_row, end_col = xlrd.xlsx.cell_name_to_rowx_colx(cells[1])
            return self._get_cell_range(sheet, start_row, end_row, start_col, end_col, as_datetime)

    def close(self):
        """Calls :meth:`~xlrd.book.Book.release_resources`."""
        self._workbook.release_resources()

    def __del__(self):
        self.close()

    def _get_cell_range(self, sheet, start_row, end_row, start_col, end_col, as_datetime):
        if start_col == end_col:
            return tuple(self._get_cell(sheet, r, start_col, as_datetime) for r in range(start_row, end_row + 1))
        elif start_row == end_row:
            return tuple(self._get_cell(sheet, start_row, c, as_datetime) for c in range(start_col, end_col + 1))
        else:
            return [tuple(self._get_cell(sheet, r, c, as_datetime) for c in range(start_col, end_col + 1))
                    for r in range(start_row, end_row + 1)]

    def _get_cell(self, sheet, row, col, as_datetime):
        cell = sheet.cell(row, col)
        t = cell.ctype
        if t == xlrd.XL_CELL_NUMBER:
            return cell.value
        elif t == xlrd.XL_CELL_DATE:
            dt = datetime(*xlrd.xldate_as_tuple(cell.value, self._workbook.datemode))
            if as_datetime:
                return dt
            else:
                return dt.isoformat(sep=' ')
        elif t == xlrd.XL_CELL_BOOLEAN:
            return bool(cell.value)
        elif t == xlrd.XL_CELL_EMPTY:
            return None
        elif t == xlrd.XL_CELL_ERROR:
            return xlrd.error_text_from_code[cell.value]
        else:
            return cell.value.strip()
