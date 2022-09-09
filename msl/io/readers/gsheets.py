"""
Read a Google Sheets spreadsheet.
"""
import os
import re

from ..google_api import (
    GDrive,
    GSheets,
    GCellType,
)
from .spreadsheet import Spreadsheet


_google_file_id_regex = re.compile(r'^1[a-zA-Z0-9_-]{43}$')


class GSheetsReader(Spreadsheet):

    def __init__(self, file, **kwargs):
        """Read a Google Sheets spreadsheet.

        This class simply provides a convenience for reading information
        from Google spreadsheets. It is not registered as a :class:`~msl.io.base.Reader`
        because the information in a spreadsheet is unstructured and therefore
        one cannot generalize how to parse a spreadsheet to create a
        :class:`~msl.io.base.Root`.

        Parameters
        ----------
        file : :class:`str`
            The ID or path of a Google Sheets spreadsheet.
        **kwargs
            All keyword arguments are passed to :class:`~msl.io.google_api.GSheets`.

        Examples
        --------
        >>> from msl.io import GSheetsReader  # doctest: +SKIP
        >>> sheets = GSheetsReader('Google Drive/registers/equipment.gsheet')  # doctest: +SKIP
        >>> sheets = GSheetsReader('1TI3pM-534SZ5DQTEZ-7HCI04648f8ZpLGbfHWJu9FSo')  # doctest: +SKIP
        """
        super(GSheetsReader, self).__init__(file)

        if not kwargs.get('read_only', True):
            raise ValueError('Must instantiate {} in read-only mode'.format(self.__class__.__name__))

        path, ext = os.path.splitext(file)
        folders, _ = os.path.split(path)
        if ext or folders or not _google_file_id_regex.match(path):
            self._spreadsheet_id = GDrive(**kwargs).file_id(path, mime_type=GSheets.MIME_TYPE)
        else:
            self._spreadsheet_id = path

        self._gsheets = GSheets(**kwargs)
        self._cached_sheet_name = None

    def read(self, cell=None, sheet=None, as_datetime=True):
        """Read values from the Google Sheets spreadsheet.

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
            returned as a string in the format of the spreadsheet cell.

        Returns
        -------
        The value(s) of the requested cell(s).

        Examples
        --------
        .. invisible-code-block: pycon

           >>> SKIP_IF_NO_GOOGLE_SHEETS_READ_TOKEN()
           >>> from msl.io import GSheetsReader
           >>> sheets = GSheetsReader('1TI3pM-534SZ5DQTEZ-7vCI04l48f8ZpLGbfEWJuCFSo', account='testing')

        >>> sheets.read()
        [('temperature', 'humidity'), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]
        >>> sheets.read('B2')
        49.82
        >>> sheets.read('A:A')
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> sheets.read('A1:B1')
        [('temperature', 'humidity')]
        >>> sheets.read('A2:B4')
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]
        """
        if not sheet:
            if self._cached_sheet_name:
                sheet = self._cached_sheet_name
            else:
                names = self.sheet_names()
                if len(names) != 1:
                    raise ValueError('{!r} contains the following sheets:\n  {}\n'
                                     'You must specify the name of the sheet to read'
                                     .format(self._file, ', '.join(repr(n) for n in names)))
                sheet = names[0]
                self._cached_sheet_name = sheet

        if cell:
            ranges = '{}!{}'.format(sheet, cell)
        else:
            ranges = sheet

        cells = self._gsheets.cells(self._spreadsheet_id, ranges=ranges)

        if sheet not in cells:
            raise ValueError('There is no sheet named {!r} in {!r}'.format(sheet, self._file))

        values = []
        for row in cells[sheet]:
            row_values = []
            for item in row:
                if item.type == GCellType.DATE:
                    value = GSheets.to_datetime(item.value).date() if as_datetime else item.formatted
                elif item.type == GCellType.DATE_TIME:
                    value = GSheets.to_datetime(item.value) if as_datetime else item.formatted
                else:
                    value = item.value
                row_values.append(value)
            values.append(tuple(row_values))

        if not cell:
            return values

        if ':' not in cell:
            if values:
                return values[0][0]
            return

        return values

    def sheet_names(self):
        """Get the names of all sheets in the Google Sheets spreadsheet.

        Returns
        -------
        :class:`tuple` of :class:`str`
            The names of all sheets.
        """
        return self._gsheets.sheet_names(self._spreadsheet_id)
