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
from .spreadsheet import Spreadsheet

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any
    from xml.etree.ElementTree import Element

    from msl.io.types import PathLike

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="ODSReader")  # pyright: ignore[reportUnreachable]


class ODSReader(Spreadsheet):
    """Read an OpenDocument Spreadsheet (*.ods* and *.fods* files, Version 1.2)."""

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

        self._ns: dict[str, str] = {
            "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
            "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
            "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        }

        self._spans: dict[int, tuple[int, Any]] = {}  # column-index: (spans-remaining, cell-value)

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
        return

    def read(  # noqa: C901, PLR0912
        self, cells: str | None = None, sheet: str | None = None, *, as_datetime: bool = True, merged: bool = False
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the OpenDocument Spreadsheet.

        Args:
            cells: The cell(s) to read. For example, `C9` will return a single value
                and `C9:G20` will return all values in the specified range. If not
                specified then returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only
                one sheet in the spreadsheet then you do not need to specify the name
                of the sheet.
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime]
                or [date][datetime.date] objects. If `False`, dates are returned as a
                string in the display format of the spreadsheet cell.
            merged: Applies to cells that are merged with other cells. If `False`, the
                value of each unmerged cell is returned, otherwise the same value is
                returned for all merged cells. In an OpenDocument Spreadsheet, the value
                of a hidden cell that is merged with a visible cell can still be retained
                (depends on how the merger was performed).

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
        >>> ods.read("A:A")
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> ods.read("A1:B1")
        [('temperature', 'humidity')]
        >>> ods.read("A2:B4")
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]

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
            raise ValueError(msg) from None

        maxsize = sys.maxsize - 1
        r1, c1, r2, c2, contains_colon = 0, 0, maxsize, maxsize, False
        if cells:
            split = cells.split(":")
            r, c1 = self.to_indices(split[0])
            r1 = 0 if r is None else r
            if len(split) > 1:
                contains_colon = True
                r, c2 = self.to_indices(split[1])
                if r is not None:
                    r2 = r
            else:
                r2, c2 = r1, c1

        self._spans.clear()
        data: list[tuple[Any, ...]] = []
        for row in self._rows(table, r1, r2):
            values = tuple(self._cell(row, c1, c2, as_datetime, merged))
            if values:
                data.append(values)

        if not contains_colon and r1 == r2 and c1 == c2:
            try:
                return data[0][0]
            except IndexError:
                return None

        return data

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

    def _cell(self, row: Element[str], start: int, stop: int, as_datetime: bool, merged: bool) -> Any:  # noqa: C901, FBT001, PLR0912
        """Yield the value of each cell between the `start` and `stop` indices in the `row`."""
        start += 1
        stop += 1
        position = 0
        for index, cell in enumerate(row):
            if merged:
                nrs = int(self._attribute(cell, "table", "number-rows-spanned", "0"))
                ncs = int(self._attribute(cell, "table", "number-columns-spanned", "0"))
                if nrs > 1 and ncs > 1:
                    value = self._value(cell, as_datetime=as_datetime)
                    for j in range(ncs):
                        self._spans[index + j] = (nrs, value)
                elif nrs > 1:
                    self._spans[index] = (nrs, self._value(cell, as_datetime=as_datetime))
                elif ncs > 1:
                    value = self._value(cell, as_datetime=as_datetime)
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
                    value = self._value(cell, as_datetime=as_datetime)
                for i in range(start, position + 1):
                    if i > stop:
                        return
                    start += 1
                    yield value
            elif position > stop:
                return
            elif merged and index in self._spans:
                remaining, span_value = self._spans[index]
                if remaining > 0:
                    if remaining == 1:
                        del self._spans[index]
                    else:
                        self._spans[index] = (remaining - 1, span_value)
                    start += 1
                    yield span_value
            else:
                start += 1
                yield self._value(cell, as_datetime=as_datetime)

    def _value(self, cell: Element[str], as_datetime: bool) -> Any:  # noqa: FBT001, PLR0911
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
            dt = datetime.fromisoformat(value)
            if dt.hour + dt.minute + dt.second + dt.microsecond == 0:
                return dt.date()
            return dt

        # typ is one of: percentage currency
        return float(self._attribute(cell, "office", "value"))
