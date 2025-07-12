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
    try:
        import lxml.etree as ET  # type: ignore[import-untyped]  # pyright: ignore[reportMissingImports]  # noqa: N812
    except ImportError:
        from xml.etree import ElementTree as ET

from ..base import Reader  # noqa: TID252
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

        This class simply provides a convenience for reading information from
        OpenDocument Spreadsheets. It is not registered as a [Reader][msl.io.base.Reader]
        because the information in an OpenDocument Spreadsheet is unstructured and therefore
        one cannot generalize how to parse an OpenDocument Spreadsheet to create a
        [Root][msl.io.base.Root].

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

        self._names: tuple[str, ...] | None = None
        self._ns: dict[str, str] = {
            "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
            "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
            "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        }

        ext = Reader.get_extension(f).lower()
        content: Element[str]
        if ext == ".ods":
            with ZipFile(f) as z:
                if (
                    z.NameToInfo.get("mimetype") is None
                    or z.read("mimetype") != b"application/vnd.oasis.opendocument.spreadsheet"
                ):
                    msg = "Unsupported OpenDocument Spreadsheet file"
                    raise ValueError(msg)

                try:
                    content = ET.XML(z.read("content.xml"))  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
                except SyntaxError as e:
                    e.msg += "\nThe ODS file might be password protected (which is not supported)"
                    raise

        elif ext == ".fods":
            with open(f, mode="rb") as fp:  # noqa: PTH123
                content = ET.XML(fp.read())  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        else:
            msg = f"Unsupported OpenDocument Spreadsheet file extension {ext!r}"
            raise ValueError(msg)

        self._tables: list[Element[str]] = content.findall(".//table:table", namespaces=self._ns)  # pyright: ignore[reportUnknownMemberType]

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter a context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        return

    def read(  # noqa: C901, PLR0912
        self, cell: str | None = None, sheet: str | None = None, *, as_datetime: bool = True
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the OpenDocument Spreadsheet.

        Args:
            cell: The cell(s) to read. For example, `C9` will return a single value
                and `C9:G20` will return all values in the specified range. If not
                specified then returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only
                one sheet in the spreadsheet then you do not need to specify the name
                of the sheet.
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime]
                or [date][datetime.date] objects. If `False`, dates are returned as a
                string in the display format of the spreadsheet cell.

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
        names = self.sheet_names()
        if not sheet:
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

        try:
            table = self._tables[names.index(name)]
        except ValueError:
            msg = f"There is no sheet named {name!r} in {self._file!r}"
            raise ValueError(msg) from None

        maxsize = sys.maxsize - 1
        r1, c1, r2, c2, contains_colon = 0, 0, maxsize, maxsize, False
        if cell:
            split = cell.split(":")
            r, c1 = self.to_indices(split[0])
            r1 = 0 if r is None else r
            if len(split) > 1:
                contains_colon = True
                r, c2 = self.to_indices(split[1])
                if r is not None:
                    r2 = r
            else:
                r2, c2 = r1, c1

        data: list[tuple[Any, ...]] = []
        for row in self._rows(table, r1, r2):
            values = tuple(self._cell(row, c1, c2, as_datetime))
            if values:
                data.append(values)

        if not contains_colon and r1 == r2 and c1 == c2:
            try:
                return data[0][0]
            except IndexError:
                return None

        return data

    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the OpenDocument Spreadsheet.

        Returns:
            The names of all sheets.
        """
        if self._names is None:
            self._names = tuple(self._attribute(t, "table", "name") for t in self._tables)
        return self._names

    def _attribute(self, element: Element[str], ns: str, name: str, default: str = "") -> str:
        """Returns the value of an attribute."""
        return element.get(f"{{{self._ns[ns]}}}{name}", default=default)

    def _rows(self, table: Element[str], start: int, stop: int) -> Generator[Element[str]]:
        """Yield all rows between `start` and `stop` in the `table`."""
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

    def _cell(self, row: Element[str], start: int, stop: int, as_datetime: bool) -> Any:  # noqa: FBT001
        """Yield the value of each cell between `start` and `stop` in the `row`."""
        start += 1
        stop += 1
        position = 0
        for cell in row:
            row_spans = int(self._attribute(cell, "table", "number-rows-spanned", "0"))
            if row_spans > 1:
                msg = "Reading row-spanned cells is not currently supported"
                raise ValueError(msg)

            col_spans = int(self._attribute(cell, "table", "number-columns-spanned", "0"))
            if col_spans > 1:
                msg = "Reading column-spanned cells is not currently supported"
                raise ValueError(msg)

            repeats = int(self._attribute(cell, "table", "number-columns-repeated", "0"))
            position += repeats or 1
            if position < start:
                continue

            if repeats:
                value = self._value(cell, as_datetime=as_datetime)
                for i in range(start, position + 1):
                    if i > stop:
                        return
                    start += 1
                    yield value
            elif position > stop:
                return
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

        # typ is one of: float percentage currency
        return float(self._attribute(cell, "office", "value"))
