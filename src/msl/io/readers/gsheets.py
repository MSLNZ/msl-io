"""Read a Google Sheets spreadsheet."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ..google_api import GCellType, GDrive, GSheets  # noqa: TID252
from .spreadsheet import Spreadsheet

if TYPE_CHECKING:
    import sys
    from typing import Any

    from .._types import PathLike  # noqa: TID252

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="GSheetsReader")  # pyright: ignore[reportUnreachable]


_google_file_id_regex = re.compile(r"^1[a-zA-Z0-9_-]{43}$")


class GSheetsReader(Spreadsheet):
    """Read a Google Sheets spreadsheet."""

    def __init__(
        self,
        file: PathLike,
        *,
        account: str | None = None,
        credentials: PathLike | None = None,
    ) -> None:
        """Read a Google Sheets spreadsheet.

        This class simply provides a convenience for reading information
        from Google spreadsheets. It is not registered as a [Reader][msl.io.base.Reader]
        because the information in a spreadsheet is unstructured and therefore
        one cannot generalize how to parse a spreadsheet to create a
        [Root][msl.io.base.Root].

        Args:
            file: The ID or path of a Google Sheets spreadsheet.
            account: Since a person may have multiple Google accounts, and multiple people
                may run the same code, this parameter decides which token to load
                to authenticate with the Google API. The value can be any text (or
                `None`) that you want to associate with a particular Google
                account, provided that it contains valid characters for a filename.
                The value that you chose when you authenticated with your `credentials`
                should be used for all future instances of this class to access that
                particular Google account. You can associate a different value with
                a Google account at any time (by passing in a different `account`
                value), but you will be asked to authenticate with your `credentials`
                again, or, alternatively, you can rename the token files located in
                [MSL_IO_DIR][msl.io.constants.MSL_IO_DIR]` to match the new `account` value.
            credentials: The path to the `client secrets` OAuth credential file. This
                parameter only needs to be specified the first time that you
                authenticate with a particular Google account or if you delete
                the token file that was created when you previously authenticated.

        **Examples:**
        ```python
        from msl.io import GSheetsReader

        # Specify the path
        sheets = GSheetsReader("Google Drive/registers/equipment.gsheet")

        # Specify the ID
        sheets = GSheetsReader("1TI3pM-534SZ5DQTEZ-7HCI04648f8ZpLGbfHWJu9FSo")
        ```
        """
        file = os.fsdecode(file)
        super().__init__(file)

        path, ext = os.path.splitext(file)  # noqa: PTH122
        folders, _ = os.path.split(path)

        self._spreadsheet_id: str
        if ext or folders or not _google_file_id_regex.match(path):
            self._spreadsheet_id = GDrive(account=account, credentials=credentials).file_id(
                path, mime_type=GSheets.MIME_TYPE
            )
        else:
            self._spreadsheet_id = path

        self._gsheets: GSheets = GSheets(account=account, credentials=credentials, read_only=True)
        self._cached_sheet_name: str | None = None

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        self.close()

    def close(self) -> None:
        """Close the connection to the GSheet API service.

        !!! note "Added in version 0.2"
        """
        self._gsheets.close()

    def read(  # noqa: C901, PLR0912
        self, cell: str | None = None, sheet: str | None = None, *, as_datetime: bool = True
    ) -> Any | list[tuple[Any, ...]]:
        """Read cell values from the Google Sheets spreadsheet.

        Args:
            cell: The cell(s) to read. For example, `C9` will return a single value
                and `C9:G20` will return all values in the specified range. If not
                specified then returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only one
                sheet in the spreadsheet then you do not need to specify the name of the sheet.
            as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
                [date][datetime.date] objects. If `False`, dates are returned as a string in
                the format of the spreadsheet cell.

        Returns:
            The value(s) of the requested cell(s).

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> SKIP_IF_NO_GOOGLE_SHEETS_READ_TOKEN()
        >>> from msl.io import GSheetsReader
        >>> sheets = GSheetsReader('1TI3pM-534SZ5DQTEZ-7vCI04l48f8ZpLGbfEWJuCFSo', account='testing')

        -->

        ```pycon
        >>> sheets.read()
        [('temperature', 'humidity'), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]
        >>> sheets.read("B2")
        49.82
        >>> sheets.read("A:A")
        [('temperature',), (20.33,), (20.23,), (20.41,), (20.29,)]
        >>> sheets.read("A1:B1")
        [('temperature', 'humidity')]
        >>> sheets.read("A2:B4")
        [(20.33, 49.82), (20.23, 46.06), (20.41, 47.06)]

        ```
        """
        if not sheet:
            if self._cached_sheet_name:
                sheet = self._cached_sheet_name
            else:
                names = self.sheet_names()
                if len(names) != 1:
                    sheet_names = ", ".join(repr(n) for n in names)
                    msg = (
                        f"{self._file} contains the following sheets:\n  {sheet_names}\n"
                        f"You must specify the name of the sheet to read"
                    )
                    raise ValueError(msg)
                sheet = names[0]
                self._cached_sheet_name = sheet

        ranges = f"{sheet}!{cell}" if cell else sheet

        cells = self._gsheets.cells(self._spreadsheet_id, ranges=ranges)

        if sheet not in cells:
            msg = f"There is no sheet named {sheet!r} in {self._file!r}"
            raise ValueError(msg)

        values: list[tuple[Any, ...]] = []
        for row in cells[sheet]:
            row_values: list[Any] = []
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

        if ":" not in cell:
            if values:
                return values[0][0]
            return None

        return values

    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the Google Sheets spreadsheet.

        Returns:
            The names of all sheets.
        """
        return self._gsheets.sheet_names(self._spreadsheet_id)
