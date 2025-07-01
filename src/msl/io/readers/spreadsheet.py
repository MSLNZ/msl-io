"""Classes for reading cells in spreadsheets."""

from __future__ import annotations

import re
import string
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

_cell_regex = re.compile(r"^([A-Z]+)(\d*)$")


class Spreadsheet(ABC):
    """Abstract base class for spreadsheets."""

    def __init__(self, file: str) -> None:
        """Abstract base class for spreadsheets.

        Args:
            file: The location of the spreadsheet on a local hard drive or on a network.
        """
        self._file: str = file

    @property
    def file(self) -> str:
        """[str][] &mdash; The location of the spreadsheet on a local hard drive or on a network."""
        return self._file

    @abstractmethod
    def read(
        self,
        cell: str | None = None,
        sheet: str | None = None,
        *,
        as_datetime: bool = True,
    ) -> Any | list[tuple[Any, ...]]:
        """Read values from the spreadsheet.

        !!! important
            You must override this method.

        Args:
            cell: The cell(s) to read. For example, `C9` will return a single value
                and `C9:G20` will return all values in the specified range. If not
                specified then returns all values in the specified `sheet`.
            sheet: The name of the sheet to read the value(s) from. If there is only one
                sheet in the spreadsheet then you do not need to specify the name of the sheet.
            as_datetime: Whether dates should be returned as [datetime.datetime][] or
                [datetime.date][] objects. If `False`, dates are returned as a string in
                the format of the spreadsheet cell.

        Returns:
            The value(s) of the requested cell(s).
        """

    @abstractmethod
    def sheet_names(self) -> tuple[str, ...]:
        """Get the names of all sheets in the spreadsheet.

        !!! important
            You must override this method.

        Returns:
            The names of all sheets.
        """

    @staticmethod
    def to_letters(index: int) -> str:
        """Convert a column index to column letters.

        Args:
            index: The column index (zero based).

        Returns:
            The corresponding spreadsheet column letter(s).

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> from msl.io.readers.spreadsheet import Spreadsheet
        >>> to_letters = Spreadsheet.to_letters

        -->

        ```pycon
        >>> to_letters(0)
        'A'
        >>> to_letters(1)
        'B'
        >>> to_letters(26)
        'AA'
        >>> to_letters(702)
        'AAA'
        >>> to_letters(494264)
        'ABCDE'

        ```
        """
        letters: list[str] = []
        uppercase = string.ascii_uppercase
        while index >= 0:
            div, mod = divmod(index, 26)
            letters.append(uppercase[mod])
            index = div - 1
        return "".join(letters[::-1])

    @staticmethod
    def to_indices(cell: str) -> tuple[int | None, int]:
        """Convert a string representation of a cell to row and column indices.

        Args:
            cell: The cell. Can be letters only (a column) or letters and a number
                (a column and a row).

        Returns:
            The (row_index, column_index). If `cell` does not contain a row number
            then the row index is `None`. The row and column index are zero based.

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> from msl.io.readers.spreadsheet import Spreadsheet
        >>> to_indices = Spreadsheet.to_indices

        -->

        ```pycon
        >>> to_indices("A")
        (None, 0)
        >>> to_indices("A1")
        (0, 0)
        >>> to_indices("AA10")
        (9, 26)
        >>> to_indices("AAA111")
        (110, 702)
        >>> to_indices("MSL123456")
        (123455, 9293)
        >>> to_indices("BIPM")
        (None, 41664)

        ```
        """
        match = _cell_regex.match(cell)
        if not match:
            msg = f"Invalid cell {cell!r}"
            raise ValueError(msg)

        letters, numbers = match.groups()
        row = max(0, int(numbers) - 1) if numbers else None
        uppercase = string.ascii_uppercase
        col = sum((26**i) * (1 + uppercase.index(c)) for i, c in enumerate(letters[::-1]))
        return row, col - 1

    @staticmethod
    def to_slices(
        cells: str, row_step: int | None = None, column_step: int | None = None
    ) -> tuple[slice[int, int | None, int | None], slice[int, int, int | None]]:
        """Convert a range of cells to slices of row and column indices.

        Args:
            cells: The cells. Can be letters only (a column) or letters and a number
                (a column and a row).
            row_step: The step-by value for the row slice.
            column_step: The step-by value for the column slice.

        Returns:
            The row [slice][], the column [slice][].

        **Examples:**
        <!-- invisible-code-block: pycon
        >>> from msl.io.readers.spreadsheet import Spreadsheet
        >>> to_slices = Spreadsheet.to_slices

        -->

        ```pycon
        >>> to_slices("A:A")
        (slice(0, None, None), slice(0, 1, None))
        >>> to_slices("A:H")
        (slice(0, None, None), slice(0, 8, None))
        >>> to_slices("B2:M10")
        (slice(1, 10, None), slice(1, 13, None))
        >>> to_slices("A5:M100", row_step=2, column_step=4)
        (slice(4, 100, 2), slice(0, 13, 4))

        ```
        """
        split = cells.split(":")
        if len(split) != 2:  # noqa: PLR2004
            msg = f"Invalid cell range {cells!r}"
            raise ValueError(msg)

        r1, c1 = Spreadsheet.to_indices(split[0])
        r2, c2 = Spreadsheet.to_indices(split[1])
        if r1 is None:
            r1 = 0
        if r2 is not None:
            r2 += 1
        c2 += 1
        return slice(r1, r2, row_step), slice(c1, c2, column_step)
