"""Read an Excel spreadsheet (*.xls* and *.xlsx* files)."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from ._xlrd import (
    XL_CELL_BOOLEAN,
    XL_CELL_DATE,
    XL_CELL_EMPTY,
    XL_CELL_ERROR,
    XL_CELL_NUMBER,
    XLDateError,
    XLRDError,
    error_text_from_code,
    open_workbook,
    xldate_as_tuple,
)
from .spreadsheet import Spreadsheet, to_ranges

if TYPE_CHECKING:
    import sys
    from collections.abc import Iterable
    from datetime import date
    from typing import Any

    from ..typing import PathLike  # noqa: TID252
    from ._xlrd import Book
    from ._xlrd.sheet import Sheet

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="ExcelReader")  # pyright: ignore[reportUnreachable]


class ExcelReader(Spreadsheet):
    """Read an Excel spreadsheet (*.xls* and *.xlsx* files)."""

    def __init__(self, file: PathLike, **kwargs: Any) -> None:
        """Read an Excel spreadsheet (*.xls* and *.xlsx* files).

        This class simply provides a convenience for reading cell values (not
        drawings or charts) from Excel spreadsheets. It is not registered as
        a [Reader][msl.io.base.Reader] because the information in a spreadsheet
        is unstructured and therefore one cannot generalize how to parse a
        spreadsheet to create a [Root][msl.io.base.Root].

        Args:
            file: The path to an Excel spreadsheet file.
            kwargs: All keyword arguments are passed to [xlrd.open_workbook][]{:target="_blank"}.
                You can use an `encoding` keyword argument as an alias for `encoding_override`.
                The default `on_demand` value is `True`.

        **Examples:**
        ```python
        from msl.io import ExcelReader
        excel = ExcelReader("lab_environment.xlsx")
        ```
        """
        f = os.fsdecode(file)
        super().__init__(f)

        # change the default on_demand value
        if "on_demand" not in kwargs:
            kwargs["on_demand"] = True

        # 'encoding' is an alias for 'encoding_override'
        encoding = kwargs.pop("encoding", None)
        if encoding is not None:
            kwargs["encoding_override"] = encoding

        self._workbook: Book = open_workbook(f, **kwargs)

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter a context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        self.close()

    def close(self) -> None:
        """Close the workbook."""
        self._workbook.release_resources()

    def read(  # noqa: PLR0913
        self,
        cells: str | None = None,
        sheet: str | None = None,
        *,
        as_datetime: bool = True,
        invalid_date: str | date | datetime | None = None,
        merged: bool = False,
        skip_rows: Iterable[int] | None = None,
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the Excel spreadsheet.

        Args:
            cells: The cell(s) to read. For example,

                * `C9` &mdash; a single value,
                * `B` &mdash; all values in column *B*,
                * `A2:D2` &mdash; all values in row 2 for columns *A B C D*,
                * `C9:G20` &mdash; all values in rows 9 to 20 for columns *C D E F G*,
                * `D,F,H:K` &mdash; all values in columns *D F H I J K*
                * `F3:H10,K` &mdash; all values in rows 3 to 10 for columns *F G H K*.

                If not specified, returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only
                one sheet in the spreadsheet then you do not need to specify the name
                of the sheet.
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
                [date][datetime.date] objects. If `False`, dates are returned as an
                ISO 8601 string.
            invalid_date: If `None`, an error is raised if a cell contains a value that
                is an invalid date. If not `None`, all cells that contain an invalid date are
                replaced with the specified value.
            merged: Applies to cells that are merged with other cells. If cells are merged, then
                only the top-left cell has the value and all other cells in the merger are empty.
                Enabling this argument is currently not supported and the value must be `False`.
            skip_rows: Row numbers to skip. The row numbers are as shown when the spreadsheet is
                viewed in Excel and are not based on the row number in the data that would be
                returned. For example, if `cells=A3:D10` and you want to skip the data in rows
                `A5:D5` and `A7:D7` then `skip_rows=[5, 7]` achieves the desired result.

        Returns:
            The value(s) of the requested cell(s).

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> from msl.io import ExcelReader
        >>> excel = ExcelReader('./tests/samples/lab_environment.xlsx')

        -->

        ```pycon
        >>> excel.read()
        [('temperature', 'humidity'), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]
        >>> excel.read("B2")
        49.82
        >>> excel.read("A")
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> excel.read("B:B")
        [('humidity',), (49.82,), (46.06,), (47.06,), (48.32,)]
        >>> excel.read("A1:B1")
        [('temperature', 'humidity')]
        >>> excel.read("A2:B4")
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]
        >>> excel.read("B,A")
        [('humidity', 'temperature'), (49.82, 20.33), (46.06, 20.23), (47.06, 20.41), (48.32, 20.29)]

        ```
        """
        if merged:
            msg = "The `merged` argument must be False to read an Excel spreadsheet"
            raise ValueError(msg)

        if not sheet:
            names = self.sheet_names()
            if len(names) == 1:
                sheet_name = names[0]
            elif not names:
                msg = "Cannot determine the names of the sheets in the Excel file"
                raise ValueError(msg)
            else:
                sheets = ", ".join(repr(n) for n in names)
                msg = (
                    f"{self.file!r} contains the following sheets:\n  {sheets}\n"
                    f"You must specify the name of the sheet to read"
                )
                raise ValueError(msg)
        else:
            sheet_name = sheet

        try:
            _sheet = self._workbook.sheet_by_name(sheet_name)
        except XLRDError:
            msg = f"A sheet named {sheet_name!r} is not in {self._file!r}"
            raise ValueError(msg) from None

        cols: range | list[int]
        nrows, ncols = _sheet.nrows, _sheet.ncols
        if cells is None:
            is_range = True
            r1, r2, cols = 0, nrows, range(ncols)
        else:
            is_range, r1, r, cols = to_ranges(cells)
            r2 = nrows if r is None else min(r, nrows)
            cols = [c for c in cols if c < ncols]

        if r1 >= nrows or not cols:
            return [] if is_range else None

        skip: set[int] = {r - r1 - 1 for r in skip_rows} if skip_rows else set()
        data = [
            tuple(self._value(_sheet, r, c, as_datetime, invalid_date) for c in cols)
            for i, r in enumerate(range(r1, r2))
            if i not in skip
        ]

        if is_range:
            return data

        try:
            return data[0][0]
        except IndexError:
            return None

    def dimensions(self, sheet: str) -> tuple[int, int]:
        """Get the number of rows and columns in a sheet.

        Args:
            sheet: The name of a sheet to get the dimensions of.

        Returns:
            The *(number of rows, number of columns)* in `sheet`.
        """
        try:
            s = self._workbook.sheet_by_name(sheet)
        except XLRDError:
            msg = f"A sheet named {sheet!r} is not in {self._file!r}"
            raise ValueError(msg) from None
        else:
            return (s.nrows, s.ncols)

    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the Excel spreadsheet.

        Returns:
            The names of all sheets.
        """
        return tuple(self._workbook.sheet_names())

    def _value(  # noqa: PLR0911
        self,
        sheet: Sheet,
        row: int,
        col: int,
        as_datetime: bool,  # noqa: FBT001
        invalid_date: str | date | datetime | None,
    ) -> Any:
        """Get the value of a cell."""
        cell = sheet.cell(row, col)
        t = cell.ctype
        if t == XL_CELL_NUMBER:
            if cell.value.is_integer():
                return int(cell.value)
            return cell.value

        if t == XL_CELL_DATE:
            try:
                tup = xldate_as_tuple(cell.value, self._workbook.datemode)
            except XLDateError as e:
                if invalid_date is not None:
                    return invalid_date
                letter = self.to_letters(col)
                msg = (
                    f"Invalid date in sheet {sheet.name!r} at cell '{letter}{row + 1}' "
                    f"[value={cell.value}, datemode={self._workbook.datemode}]. "
                    "Specify a value for `invalid_date` to suppress this error."
                )
                raise type(e)(msg) from None
            dt = datetime(*tup)  # noqa: DTZ001
            if dt.hour + dt.minute + dt.second + dt.microsecond == 0:
                _date = dt.date()
                return _date if as_datetime else str(_date)
            return dt if as_datetime else str(dt)

        if t == XL_CELL_BOOLEAN:
            return bool(cell.value)

        if t == XL_CELL_EMPTY:
            return None

        if t == XL_CELL_ERROR:
            return error_text_from_code[cell.value]

        return cell.value.strip()
