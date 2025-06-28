"""Read a data table from a file."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .base import Reader
from .node import Dataset
from .readers import ExcelReader, GSheetsReader
from .utils import get_basename

if TYPE_CHECKING:
    from typing import IO, Any

    from numpy.typing import DTypeLike

    from ._types import PathLike

_spreadsheet_top_left_regex = re.compile(r"^([A-Z]+)(\d+)$")
_spreadsheet_range_regex = re.compile(r"^[A-Z]+\d*:[A-Z]+\d*$")


extension_delimiter_map: dict[str, str] = {".csv": ","}
"""The delimiter to use to separate columns in a table based on the file extension.

If the `delimiter` is not specified when calling the :func:`~msl.io.read_table` function then this
extension-delimiter map is used to determine the value of the `delimiter`. If the file extension
is not in the map then the value of the `delimiter` is :data:`None` (i.e., split columns by any
whitespace).

Examples:
You can customize your own map by adding key-value pairs

```pycon
>>> from msl.io import extension_delimiter_map
>>> extension_delimiter_map['.txt'] = '\\t'

```

"""


def read_table_text(file: IO[bytes] | IO[str] | PathLike, **kwargs: Any) -> Dataset:
    """Read a data table from a text-based file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Args:
        file: The file to read.
        kwargs: All keyword arguments are passed to [loadtxt][numpy.loadtxt]. If the
            `delimiter` is not specified and the `file` has ``csv`` as the file
            extension then the `delimiter` is automatically set to be `,`.

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
        [Metadata][msl.io.metadata.Metadata].
    """
    if kwargs.get("unpack", False):
        msg = "Cannot use the 'unpack' option"
        raise ValueError(msg)

    if "delimiter" not in kwargs:
        ext = Reader.get_extension(file).lower()
        kwargs["delimiter"] = extension_delimiter_map.get(ext)

    if "skiprows" not in kwargs:
        kwargs["skiprows"] = 0
    kwargs["skiprows"] += 1  # Reader.get_lines is 1-based, np.loadtxt is 0-based

    header: list[bytes] | list[str]
    first_line = Reader.get_lines(file, kwargs["skiprows"], kwargs["skiprows"])
    if not first_line:
        header, data = [], np.array([])
    else:
        header = first_line[0].split(kwargs["delimiter"])  # pyright: ignore[reportArgumentType]
        # Calling np.loadtxt (on Python 3.5, 3.6 and 3.7) on a file
        # on a mapped drive could raise an OSError. This occurred
        # when a local folder was shared and then mapped on the same
        # computer. Opening the file using open() and then passing
        # in the file handle to np.loadtxt is more universal
        if isinstance(file, (bytes, str, os.PathLike)):
            with Path(os.fsdecode(file)).open() as f:
                data = np.loadtxt(f, **kwargs)
        else:
            data = np.loadtxt(file, **kwargs)

        use_cols = kwargs.get("usecols")
        if use_cols:
            if isinstance(use_cols, int):
                use_cols = [use_cols]
            header = [header[i] for i in use_cols]  # pyright: ignore[reportAssignmentType]

    return Dataset(
        name=get_basename(file), parent=None, read_only=True, data=data, header=np.asarray(header, dtype=str)
    )


def read_table_excel(
    file: IO[bytes] | IO[str] | PathLike,
    *,
    cells: str | None = None,
    sheet: str | None = None,
    as_datetime: bool = True,
    dtype: DTypeLike = None,
    **kwargs: Any,
) -> Dataset:
    """Read a data table from an Excel spreadsheet.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Args:
        file: The file to read.
        cells: The cells to read. For example, `C9` will start at cell C9 and
            include all values until the end of the spreadsheet, `A:C` includes
            all rows in columns A, B and C, and, `C9:G20` includes values from
            only the specified cells. If not specified then returns all values
            from the specified `sheet`.
        sheet: The name of the sheet to read the data from. If there is only one sheet
            in the workbook then you do not need to specify the name of the sheet.
        as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
            [date][datetime.date] objects. If `False`, dates are returned as a [str][].
        dtype: The data type(s) to use for the table.
        kwargs: All additional keyword arguments are passed to [xlrd.open_workbook][].
            Can use an `encoding` keyword argument as an alias for `encoding_override`.

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
        [Metadata][msl.io.metadata.Metadata].
    """
    file = os.fsdecode(file) if isinstance(file, (bytes, str, os.PathLike)) else str(file.name)

    with ExcelReader(file, **kwargs) as excel:
        if cells is not None and not _spreadsheet_range_regex.match(cells):
            match = _spreadsheet_top_left_regex.match(cells)
            if not match:
                msg = f"Invalid cell {cells!r}"
                raise ValueError(msg)
            name = sheet or excel.workbook.sheet_names()[0]
            s = excel.workbook.sheet_by_name(name)
            letters = excel.to_letters(s.ncols - 1)
            row = match.group(2)
            cells += f":{letters}{row}"
        table = excel.read(cell=cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def read_table_gsheets(
    file: IO[bytes] | IO[str] | PathLike,
    cells: str | None = None,
    sheet: str | None = None,
    *,
    as_datetime: bool = True,
    dtype: DTypeLike = None,
    **kwargs: Any,
) -> Dataset:
    """Read a data table from a Google Sheets spreadsheet.

    !!! attention
        You must have already performed the instructions specified in
        [GDrive][msl.io.google_api.GDrive] and in [GSheets][msl.io.google_api.GSheets]
        to be able to use this function.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Args:
        file: The file to read. Can be the ID of a Google Sheets spreadsheet.
        cells: The cells to read. For example, `C9` will start at cell C9 and
            include all values until the end of the spreadsheet, `A:C` includes
            all rows in columns A, B and C, and, `C9:G20` includes
            values from only the specified cells. If not specified then returns
            all values from the specified `sheet`.
        sheet: The name of the sheet to read the data from. If there is only one sheet
            in the spreadsheet then you do not need to specify the name of the sheet.
        as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
            [date][datetime.date] objects. If `False`, dates are returned as a [str][].
        dtype: The data type(s) to use for the table.
        kwargs: All additional keyword arguments are passed to [GSheetsReader][msl.io.readers.gsheets.GSheetsReader].

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
        [Metadata][msl.io.metadata.Metadata].
    """
    file = os.fsdecode(file) if isinstance(file, (bytes, str, os.PathLike)) else str(file.name)

    with GSheetsReader(file, **kwargs) as sheets:
        if cells is not None and not _spreadsheet_range_regex.match(cells):
            if not _spreadsheet_top_left_regex.match(cells):
                msg = f"Invalid cell {cells!r}"
                raise ValueError(msg)

            r, c = sheets.to_indices(cells)
            data = sheets.read(sheet=sheet, as_datetime=as_datetime)
            table = [row[c:] for row in data[r:]]
        else:
            table = sheets.read(cell=cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def _spreadsheet_to_dataset(table: Any | list[tuple[Any, ...]], file: str, dtype: DTypeLike) -> Dataset:
    header: Any
    data: Any
    if not table:
        header, data = [], []
    elif len(table) == 1:
        header, data = table[0], []
    elif len(table[0]) == 1:  # a single column
        header, data = table[0], [row[0] for row in table[1:]]
    else:
        header, data = table[0], table[1:]
        if len(data) == 1:  # a single row
            data = data[0]

    return Dataset(
        name=get_basename(file),
        parent=None,
        read_only=True,
        data=data,
        dtype=dtype,
        header=np.asarray(header, dtype=str),
    )
