"""
Read an Excel spreadsheet (.xls and .xlsx).
"""
from datetime import datetime

import xlrd

from .spreadsheet import Spreadsheet


class ExcelReader(Spreadsheet):

    def __init__(self, file, **kwargs):
        """Read an Excel spreadsheet (.xls and .xlsx).

        This class simply provides a convenience for reading information
        from Excel spreadsheets. It is not registered as a :class:`~msl.io.base_io.Reader`
        because the information in an Excel spreadsheet is unstructured and therefore
        one cannot generalize how to parse an Excel spreadsheet to create a
        :class:`~msl.io.base_io.Root`.

        Parameters
        ----------
        file : :class:`str`
            The location of an Excel spreadsheet on a local hard drive or on a network.
        **kwargs
            All keyword arguments are passed to :func:`~xlrd.open_workbook`. Can use
            an `encoding` keyword argument as an alias for `encoding_override`. The
            default `on_demand` value is :data:`True`.

        Examples
        --------
        >>> from msl.io import ExcelReader  # doctest: +SKIP
        >>> excel = ExcelReader('lab_environment.xlsx')  # doctest: +SKIP
        """
        super(ExcelReader, self).__init__(file)

        # change the default on_demand value
        if 'on_demand' not in kwargs:
            kwargs['on_demand'] = True

        # 'encoding' is an alias for 'encoding_override'
        encoding = kwargs.pop('encoding', None)
        if encoding is not None:
            kwargs['encoding_override'] = encoding

        self._workbook = xlrd.open_workbook(file, **kwargs)

    @property
    def workbook(self):
        """:class:`~xlrd.book.Book`: The workbook instance."""
        return self._workbook

    def close(self):
        """Calls :meth:`~xlrd.book.Book.release_resources`."""
        self._workbook.release_resources()

    def read(self, cell=None, sheet=None, as_datetime=True):
        """Read values from the Excel spreadsheet.

        Parameters
        ----------
        cell : :class:`str`, optional
            The cell(s) to read. For example, ``C9`` will return a single value
            and ``C9:G20`` will return all values in the specified range. If not
            specified then returns all values in the specified `sheet`.
        sheet : :class:`str`, optional
            The name of the sheet to read the value(s) from. If there is only
            one sheet in the spreadsheet then you do not need to specify the name
            of the sheet.
        as_datetime : :class:`bool`, optional
            Whether dates should be returned as :class:`~datetime.datetime` or
            :class:`~datetime.date` objects. If :data:`False` then dates are
            returned as an ISO 8601 string.

        Returns
        -------
        The value(s) of the requested cell(s).

        Examples
        --------
        .. invisible-code-block: pycon

           >>> from msl.io import ExcelReader
           >>> excel = ExcelReader('./tests/samples/lab_environment.xlsx')

        >>> excel.read()
        [('temperature', 'humidity'), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]
        >>> excel.read('B2')
        49.82
        >>> excel.read('A:A')
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> excel.read('A1:B1')
        [('temperature', 'humidity')]
        >>> excel.read('A2:B4')
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]
        """
        if not sheet:
            names = self.sheet_names()
            if len(names) > 1:
                raise ValueError('{!r} contains the following sheets:\n  {}\n'
                                 'You must specify the name of the sheet to read'
                                 .format(self._file, ', '.join(repr(n) for n in names)))
            sheet_name = names[0]
        else:
            sheet_name = sheet

        try:
            sheet = self._workbook.sheet_by_name(sheet_name)
        except xlrd.XLRDError:
            # TODO want to raise ValueError without nested exceptions
            #  Can "raise from None" when dropping Python 2 support
            sheet = None

        if sheet is None:
            raise ValueError('There is no sheet named {!r} in {!r}'.format(sheet_name, self._file))

        if not cell:
            return [tuple(self._value(sheet, r, c, as_datetime) for c in range(sheet.ncols))
                    for r in range(sheet.nrows)]

        split = cell.split(':')
        r1, c1 = self.to_indices(split[0])
        if r1 is None:
            r1 = 0

        if len(split) == 1:
            try:
                return self._value(sheet, r1, c1, as_datetime)
            except IndexError:
                return

        if r1 >= sheet.nrows or c1 >= sheet.ncols:
            return []

        r2, c2 = self.to_indices(split[1])
        r2 = sheet.nrows if r2 is None else min(r2+1, sheet.nrows)
        c2 = min(c2+1, sheet.ncols)
        return [tuple(self._value(sheet, r, c, as_datetime) for c in range(c1, c2))
                for r in range(r1, r2)]

    def sheet_names(self):
        """Get the names of all sheets in the Excel spreadsheet.

        Returns
        -------
        :class:`tuple` of :class:`str`
            The names of all sheets.
        """
        return tuple(self._workbook.sheet_names())

    def _value(self, sheet, row, col, as_datetime):
        """Get the value of a cell."""
        cell = sheet.cell(row, col)
        t = cell.ctype
        if t == xlrd.XL_CELL_NUMBER:
            if cell.value.is_integer():
                return int(cell.value)
            return cell.value
        elif t == xlrd.XL_CELL_DATE:
            dt = datetime(*xlrd.xldate_as_tuple(cell.value, self._workbook.datemode))
            if dt.hour + dt.minute + dt.second + dt.microsecond == 0:
                dt = dt.date()
            if as_datetime:
                return dt
            return str(dt)
        elif t == xlrd.XL_CELL_BOOLEAN:
            return bool(cell.value)
        elif t == xlrd.XL_CELL_EMPTY:
            return None
        elif t == xlrd.XL_CELL_ERROR:
            return xlrd.error_text_from_code[cell.value]
        else:
            return cell.value.strip()
