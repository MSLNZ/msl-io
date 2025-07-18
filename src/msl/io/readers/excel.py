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
    XLRDError,
    error_text_from_code,
    open_workbook,
    xldate_as_tuple,
)
from .spreadsheet import Spreadsheet

if TYPE_CHECKING:
    import sys
    from typing import Any

    from ..types import PathLike  # noqa: TID252
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

        This class simply provides a convenience for reading information from
        Excel spreadsheets. It is not registered as a [Reader][msl.io.base.Reader]
        because the information in an Excel spreadsheet is unstructured and therefore
        one cannot generalize how to parse an Excel spreadsheet to create a
        [Root][msl.io.base.Root].

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

    @property
    def workbook(self) -> Book:
        """[Book][xlrd.book.Book] &mdash; The workbook instance."""
        return self._workbook

    def close(self) -> None:
        """Close the workbook."""
        self._workbook.release_resources()

    def read(  # noqa: C901
        self, cells: str | None = None, sheet: str | None = None, *, as_datetime: bool = True, merged: bool = False
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the Excel spreadsheet.

        Args:
            cells: The cell(s) to read. For example, `C9` will return a single value
                and `C9:G20` will return all values in the specified range. If not
                specified then returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only
                one sheet in the spreadsheet then you do not need to specify the name
                of the sheet.
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
                [date][datetime.date] objects. If `False`, dates are returned as an
                ISO 8601 string.
            merged: Applies to cells that are merged with other cells. If cells are merged, then
                only the top-left cell has the value and all other cells in the merger are empty.
                Enabling this argument is currently not supported and the value must be `False`.

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
        >>> excel.read("A:A")
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> excel.read("A1:B1")
        [('temperature', 'humidity')]
        >>> excel.read("A2:B4")
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]

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

        if not cells:
            return [
                tuple(self._value(_sheet, r, c, as_datetime) for c in range(_sheet.ncols)) for r in range(_sheet.nrows)
            ]

        split = cells.split(":")
        r1, c1 = self.to_indices(split[0])
        if r1 is None:
            r1 = 0

        if len(split) == 1:
            try:
                return self._value(_sheet, r1, c1, as_datetime=as_datetime)
            except IndexError:
                return None

        if r1 >= _sheet.nrows or c1 >= _sheet.ncols:
            return []

        r2, c2 = self.to_indices(split[1])
        r2 = _sheet.nrows if r2 is None else min(r2 + 1, _sheet.nrows)
        c2 = min(c2 + 1, _sheet.ncols)
        return [tuple(self._value(_sheet, r, c, as_datetime) for c in range(c1, c2)) for r in range(r1, r2)]

    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the Excel spreadsheet.

        Returns:
            The names of all sheets.
        """
        return tuple(self._workbook.sheet_names())

    def _value(self, sheet: Sheet, row: int, col: int, as_datetime: bool) -> Any:  # noqa: FBT001, PLR0911
        """Get the value of a cell."""
        cell = sheet.cell(row, col)
        t = cell.ctype
        if t == XL_CELL_NUMBER:
            if cell.value.is_integer():
                return int(cell.value)
            return cell.value

        if t == XL_CELL_DATE:
            tup = xldate_as_tuple(cell.value, self._workbook.datemode)
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
