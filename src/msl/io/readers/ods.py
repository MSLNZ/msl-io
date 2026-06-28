"""Read an OpenDocument Spreadsheet (*.ods* and *.fods* files, Version 1.2)."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import TYPE_CHECKING
from zipfile import ZipFile

try:
    import defusedxml.ElementTree as ET  # type: ignore[import-untyped]  # pyright: ignore[reportMissingModuleSource]  # noqa: N817
except ImportError:
    from xml.etree import ElementTree as ET

from ..utils import get_extension  # noqa: TID252
from .spreadsheet import Spreadsheet, to_ranges

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from datetime import date
    from typing import Any, ClassVar
    from xml.etree.ElementTree import Element

    from msl.io.typing import PathLike

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="ODSReader")  # pyright: ignore[reportUnreachable]


class ODSReader(Spreadsheet):
    """Read an OpenDocument Spreadsheet (*.ods* and *.fods* files, Version 1.2)."""

    _ns: ClassVar[dict[str, str]] = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }

    def __init__(self, file: PathLike, **kwargs: Any) -> None:  # noqa: ARG002
        """Read an OpenDocument Spreadsheet (*.ods* and *.fods* files, Version 1.2).

        This class simply provides a convenience for reading cell values (not
        drawings or charts) from OpenDocument Spreadsheets. It is not registered
        as a [Reader][msl.io.base.Reader] because the information in a spreadsheet
        is unstructured and therefore one cannot generalize how to parse a
        spreadsheet to create a [Root][msl.io.base.Root].

        !!! tip
            If [defusedxml](https://pypi.org/project/defusedxml/){:target="_blank"} is installed,
            that package is used to parse the contents of the file instead of the
            [xml][]{:target="_blank"} module.

        Args:
            file: The path to an OpenDocument Spreadsheet file.
            kwargs: All keyword arguments are ignored.

        **Examples:**
        ```python
        from msl.io import ODSReader
        ods = ODSReader("lab_environment.ods")
        ```
        """
        f = os.fsdecode(file)
        super().__init__(f)

        self._spans: dict[int, tuple[int, Any]] = {}  # column-index: (spans-remaining, cell-value)
        self._row_data: dict[int, Any] = {}  # column-index: cell-value

        ext = get_extension(f).lower()
        content: Element[str]
        if ext == ".ods":
            with ZipFile(f) as z:
                try:
                    content = ET.XML(z.read("content.xml"))
                except SyntaxError as e:
                    e.msg += "\nThe ODS file might be password protected (which is not supported)"
                    raise
        elif ext == ".fods":
            with open(f, mode="rb") as fp:  # noqa: PTH123
                content = ET.XML(fp.read())
        else:
            msg = f"Unsupported OpenDocument Spreadsheet file extension {ext!r}"
            raise ValueError(msg)

        self._tables: dict[str, Element[str]] = {
            self._attribute(t, "table", "name"): t for t in content.findall(".//table:table", namespaces=self._ns)
        }

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter a context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        self.close()

    def close(self) -> None:
        """Free memory resources that are used to read the OpenDocument Spreadsheet."""
        self._tables.clear()
        self._spans.clear()
        self._row_data.clear()

    def read(  # noqa: C901, PLR0912, PLR0913
        self,
        cells: str | None = None,
        sheet: str | None = None,
        *,
        as_datetime: bool = True,
        invalid_date: str | date | datetime | None = None,
        merged: bool = False,
        skip_rows: Iterable[int] | None = None,
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the OpenDocument Spreadsheet.

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
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime]
                or [date][datetime.date] objects. If `False`, dates are returned as a
                string in the display format of the spreadsheet cell.
            invalid_date: If `None`, an error is raised if a cell contains a value that
                is an invalid date. If not `None`, all cells that contain an invalid date are
                replaced with the specified value.
            merged: Applies to cells that are merged with other cells. If `False`, the
                value of each unmerged cell is returned, otherwise the same value is
                returned for all merged cells. In an OpenDocument Spreadsheet, the value
                of a hidden cell that is merged with a visible cell can still be retained
                (depends on how the merger was performed).
            skip_rows: Row numbers to skip. The row numbers are as shown when the spreadsheet
                is viewed in the OpenDocument application and are not based on the row number
                in the data that would be returned. For example, if `cells="A3:D10"` and you
                want to skip the data in rows `A5:D5` and `A7:D7` then `skip_rows=[5, 7]`
                achieves the desired result.

        Returns:
            The value(s) of the requested cell(s).

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> from msl.io import ODSReader
        >>> ods = ODSReader('./tests/samples/lab_environment.ods')

        -->

        ```pycon
        >>> ods.read()
        [('temperature', 'humidity'), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]
        >>> ods.read("B2")
        49.82
        >>> ods.read("A")
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> ods.read("B:B")
        [('humidity',), (49.82,), (46.06,), (47.06,), (48.32,)]
        >>> ods.read("A1:B1")
        [('temperature', 'humidity')]
        >>> ods.read("A2:B4")
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]
        >>> ods.read("B,A")
        [('humidity', 'temperature'), (49.82, 20.33), (46.06, 20.23), (47.06, 20.41), (48.32, 20.29)]

        ```
        """
        if not sheet:
            names = self.sheet_names()
            if len(names) == 1:
                name = names[0]
            elif not names:
                msg = "Cannot determine the names of the sheets in the OpenDocument file"
                raise ValueError(msg)
            else:
                sheets = ", ".join(repr(n) for n in names)
                msg = (
                    f"{self.file!r} contains the following sheets:\n  {sheets}\n"
                    f"You must specify the name of the sheet to read"
                )
                raise ValueError(msg)
        else:
            name = sheet

        table = self._tables.get(name)
        if table is None:
            msg = f"A sheet named {sheet!r} is not in {self._file!r}"
            raise ValueError(msg)

        maxsize = sys.maxsize - 1
        if cells is None:
            is_range = True
            r1, r2 = 0, maxsize
            c1, c2 = 0, maxsize
            self._row_data.clear()
        else:
            is_range, r1, r, cols = to_ranges(cells)
            r2 = maxsize if r is None else r - 1
            c1, c2 = min(cols), max(cols)
            self._row_data = dict.fromkeys(cols, b"-")  # A cell cannot contain bytes so b"-" cannot be a cell value

        self._spans.clear()
        data: list[tuple[Any, ...]] = []
        skip: set[int] = {r - r1 - 1 for r in skip_rows} if skip_rows else set()
        for i, row in enumerate(self._rows(table, r1, r2)):
            if i in skip:
                continue
            values = tuple(self._cell(name, row, c1, c2, as_datetime, merged, invalid_date))
            if values:
                data.append(values)

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
        table = self._tables.get(sheet)
        if table is None:
            msg = f"A sheet named {sheet!r} is not in {self._file!r}"
            raise ValueError(msg) from None

        num_cols = 0
        for col in table.findall(".//table:table-column", namespaces=self._ns):
            num_cols += int(self._attribute(col, "table", "number-columns-repeated", "1"))

        num_rows = sum(1 for _ in self._rows(table, 0, sys.maxsize - 1))
        return (num_rows, num_cols)

    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the OpenDocument Spreadsheet.

        Returns:
            The names of all sheets.
        """
        return tuple(self._tables.keys())

    def _attribute(self, element: Element[str], ns: str, name: str, default: str = "") -> str:
        """Returns the value of an attribute."""
        return element.get(f"{{{self._ns[ns]}}}{name}", default=default)

    def _rows(self, table: Element[str], start: int, stop: int) -> Generator[Element[str]]:
        """Yield all rows between the `start` and `stop` indices in the `table`."""
        start += 1
        stop += 1
        position = 0
        for row in table.findall(".//table:table-row", namespaces=self._ns):
            repeats = int(self._attribute(row, "table", "number-rows-repeated", "0"))
            position += repeats or 1
            if position < start:
                continue

            if repeats:
                for i in range(start, position + 1):
                    if i > stop:
                        return
                    start += 1
                    yield row
            elif position > stop:
                return
            else:
                start += 1
                yield row

    def _cell(  # noqa: C901, PLR0912, PLR0913, PLR0915
        self,
        sheet: str,
        row: Element[str],
        start: int,
        stop: int,
        as_datetime: bool,  # noqa: FBT001
        merged: bool,  # noqa: FBT001
        invalid_date: str | date | datetime | None,
    ) -> list[Any]:
        """Yield the value of each cell between the `start` and `stop` indices in the `row`."""
        start += 1
        stop += 1
        position = 0
        column = start - 1
        values: list[Any] = []
        for index, cell in enumerate(row):
            if merged:
                nrs = int(self._attribute(cell, "table", "number-rows-spanned", "0"))
                ncs = int(self._attribute(cell, "table", "number-columns-spanned", "0"))
                if nrs > 1 and ncs > 1:
                    value = self._value(sheet, cell, as_datetime, invalid_date)
                    for j in range(ncs):
                        self._spans[index + j] = (nrs, value)
                elif nrs > 1:
                    self._spans[index] = (nrs, self._value(sheet, cell, as_datetime, invalid_date))
                elif ncs > 1:
                    value = self._value(sheet, cell, as_datetime, invalid_date)
                    self._spans[index] = (1, value)
                    # The following will be consumed by the "covered-table-cell" element in the next `row` iteration
                    self._spans[index + 1] = (ncs - 1, value)

            repeats = int(self._attribute(cell, "table", "number-columns-repeated", "0"))
            position += repeats or 1
            if position < start:
                continue

            if repeats:
                if merged and index in self._spans:
                    _, value = self._spans[index]
                    del self._spans[index]
                else:
                    value = self._value(sheet, cell, as_datetime, invalid_date)
                for i in range(start, position + 1):
                    if i > stop:
                        break
                    if not self._row_data:
                        values.append(value)
                    elif column in self._row_data:
                        self._row_data[column] = value
                    column += 1
                    start += 1
            elif position > stop:
                break
            elif merged and index in self._spans:
                remaining, span_value = self._spans[index]
                if remaining > 0:
                    if remaining == 1:
                        del self._spans[index]
                    else:
                        self._spans[index] = (remaining - 1, span_value)
                    if not self._row_data:
                        values.append(span_value)
                    elif column in self._row_data:
                        self._row_data[column] = span_value
                    column += 1
                    start += 1
            else:
                value = self._value(sheet, cell, as_datetime, invalid_date)
                if not self._row_data:
                    values.append(value)
                elif column in self._row_data:
                    self._row_data[column] = value
                column += 1
                start += 1

        return values or [v for v in self._row_data.values() if v != b"-"]

    def _value(  # noqa: C901, PLR0911
        self,
        sheet: str,
        cell: Element[str],
        as_datetime: bool,  # noqa: FBT001
        invalid_date: str | date | datetime | None,
    ) -> Any:
        """Returns the value of a table-cell as a Python object."""
        # See Section 19.385 office:value-type
        # https://docs.oasis-open.org/office/v1.2/os/OpenDocument-v1.2-os-part1.html
        typ = self._attribute(cell, "office", "value-type")
        p = cell.find("text:p", namespaces=self._ns)
        if p is None or p.text is None:
            return None

        if typ in {"", "string", "time"}:
            return p.text

        if typ == "float":
            val = float(self._attribute(cell, "office", "value"))
            if val.is_integer():
                return int(val)
            return val

        if typ == "boolean":
            return p.text == "TRUE"

        if typ == "date":
            if not as_datetime:
                return p.text

            value = self._attribute(cell, "office", "date-value")
            try:
                dt = datetime.fromisoformat(value)
            except ValueError:
                if invalid_date is not None:
                    return invalid_date
                msg = (
                    f"Invalid isoformat date {value!r} in sheet {sheet!r}. "
                    "Specify a value for `invalid_date` to suppress this error."
                )
                raise ValueError(msg) from None
            if dt.hour + dt.minute + dt.second + dt.microsecond == 0:
                return dt.date()
            return dt

        # typ is one of: percentage currency
        return float(self._attribute(cell, "office", "value"))
