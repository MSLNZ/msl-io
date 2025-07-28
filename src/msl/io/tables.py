"""Read tabular data from a file."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .node import Dataset
from .readers import ExcelReader, GSheetsReader, ODSReader
from .utils import get_basename, get_extension, get_lines

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import DTypeLike

    from .types import PathLike, ReadLike

_spreadsheet_top_left_regex = re.compile(r"^([A-Z]+)(\d+)$")
_spreadsheet_range_regex = re.compile(r"^[A-Z]+\d*:[A-Z]+\d*$")


def _header_dtype(dtype: str, header: list[str]) -> np.dtype:
    """Return a np.dtype using the header for the field names."""
    _, *remaining = dtype.split(":")
    data_types = "".join(remaining).rstrip()
    if not data_types:
        return np.dtype({"names": header, "formats": [np.double] * len(header)})

    splitted = [h.strip() for h in data_types.split(",")]
    formats = [splitted[0]] * len(header) if len(splitted) == 1 else splitted
    return np.dtype({"names": header, "formats": formats})


extension_delimiter_map: dict[str, str] = {".csv": ","}
"""The delimiter to use to separate columns in a table based on the file extension.

If the `delimiter` keyword is not specified when calling the [read_table][msl.io.tables.read_table] function
then this extension-delimiter map is used to determine the value of the delimiter to use to separate the columns
in a text-based file format. If the file extension is not in the map, then columns are split by any whitespace.

!!! example "See the [Overview][extension-delimiter-map] for an example."
"""


def read_table_text(file: PathLike | ReadLike, **kwargs: Any) -> Dataset:
    """Read a data table from a text-based file.

    The generic way to read any table is with the [read_table][msl.io.tables.read_table] function.

    Args:
        file: The file to read.
        kwargs: All keyword arguments are passed to numpy [loadtxt][numpy.loadtxt]. If the
            `delimiter` is not specified and the `file` has `.csv` as the file
            extension then the `delimiter` is automatically set to be `,` (see
            [extension_delimiter_map][msl.io.tables.extension_delimiter_map]
            for more details).

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
            [Metadata][msl.io.metadata.Metadata].
    """
    if kwargs.get("unpack", False):
        msg = "Cannot use the 'unpack' option"
        raise ValueError(msg)

    if "delimiter" not in kwargs:
        ext = get_extension(file).lower()
        kwargs["delimiter"] = extension_delimiter_map.get(ext)

    if "skiprows" not in kwargs:
        kwargs["skiprows"] = 0
    kwargs["skiprows"] += 1  # Reader.get_lines is 1-based, np.loadtxt is 0-based

    first_line = [
        h.decode() if isinstance(h, bytes) else h for h in get_lines(file, kwargs["skiprows"], kwargs["skiprows"])
    ]

    if not first_line:
        header, data = [], np.array([])
    else:
        header = first_line[0].split(kwargs["delimiter"])

        use_cols = kwargs.get("usecols")
        if use_cols:
            if isinstance(use_cols, int):
                use_cols = [use_cols]
            header = [header[i] for i in use_cols]

        dtype = kwargs.get("dtype")
        if isinstance(dtype, str) and dtype.startswith("header"):
            kwargs["dtype"] = _header_dtype(dtype, header)

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

    return Dataset(
        name=get_basename(file), parent=None, read_only=True, data=data, header=np.asarray(header, dtype=str)
    )


def read_table_excel(
    file: PathLike | ReadLike,
    *,
    cells: str | None = None,
    sheet: str | None = None,
    as_datetime: bool = True,
    dtype: DTypeLike = None,
    **kwargs: Any,
) -> Dataset:
    """Read a data table from an Excel spreadsheet.

    The generic way to read any table is with the [read_table][msl.io.tables.read_table] function.

    Args:
        file: The file to read.
        cells: The cells to read. For example, `C9` (i.e, specifying only the top-left cell
            of the table) will start at cell C9 and include all columns to the right and
            all rows below C9, `A:C` includes all rows in columns A, B and C, and, `C9:G20`
            includes only the specified cells. If not specified, assumes that the table
            starts at cell `A1` and returns all cells from the specified `sheet`.
        sheet: The name of the sheet to read the data from. If there is only one sheet
            in the workbook then you do not need to specify the name of the sheet.
        as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
            [date][datetime.date] objects. If `False`, dates are returned as an
            ISO 8601 string.
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
            name = sheet or excel.sheet_names()[0]
            num_rows, num_cols = excel.dimensions(name)
            letters = excel.to_letters(num_cols - 1)
            cells += f":{letters}{num_rows}"
        table = excel.read(cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def read_table_gsheets(
    file: PathLike | ReadLike,
    cells: str | None = None,
    sheet: str | None = None,
    *,
    as_datetime: bool = True,
    dtype: DTypeLike = None,
    **kwargs: Any,
) -> Dataset:
    """Read a data table from a Google Sheets spreadsheet.

    !!! note
        You must have already performed the instructions specified in
        [GDrive][msl.io.google_api.GDrive] and in [GSheets][msl.io.google_api.GSheets]
        to be able to use this function.

    The generic way to read any table is with the [read_table][msl.io.tables.read_table] function.

    Args:
        file: The file to read. Can be the ID of a Google Sheets spreadsheet.
        cells: The cells to read. For example, `C9` (i.e, specifying only the top-left cell
            of the table) will start at cell C9 and include all columns to the right and
            all rows below C9, `A:C` includes all rows in columns A, B and C, and, `C9:G20`
            includes only the specified cells. If not specified, assumes that the table
            starts at cell `A1` and returns all cells from the specified `sheet`.
        sheet: The name of the sheet to read the data from. If there is only one sheet
            in the spreadsheet then you do not need to specify the name of the sheet.
        as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
            [date][datetime.date] objects. If `False`, dates are returned as a string in
            the display format of the spreadsheet cell.
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
            table = sheets.read(cells, sheet=sheet, as_datetime=as_datetime)

    return _spreadsheet_to_dataset(table, file, dtype)


def read_table_ods(  # noqa: PLR0913
    file: PathLike | ReadLike,
    *,
    cells: str | None = None,
    sheet: str | None = None,
    as_datetime: bool = True,
    merged: bool = False,
    dtype: DTypeLike = None,
    **kwargs: Any,
) -> Dataset:
    """Read a data table from an OpenDocument Spreadsheet.

    The generic way to read any table is with the [read_table][msl.io.tables.read_table] function.

    Args:
        file: The file to read.
        cells: The cells to read. For example, `C9` (i.e, specifying only the top-left cell
            of the table) will start at cell C9 and include all columns to the right and
            all rows below C9, `A:C` includes all rows in columns A, B and C, and, `C9:G20`
            includes only the specified cells. If not specified, assumes that the table
            starts at cell `A1` and returns all cells from the specified `sheet`.
        sheet: The name of the sheet to read the data from. If there is only one sheet
            in the OpenDocument then you do not need to specify the name of the sheet.
        as_datetime: Whether dates should be returned as [datetime][datetime.datetime] or
            [date][datetime.date] objects. If `False`, dates are returned as a string in
            the display format of the spreadsheet cell.
        merged: Applies to cells that are merged with other cells. If `False`, the
            value of each unmerged cell is returned, otherwise the same value is
            returned for all merged cells. In an OpenDocument Spreadsheet, the value
            of a hidden cell that is merged with a visible cell can still be retained
            (depends on how the merger was performed).
        dtype: The data type(s) to use for the table.
        kwargs: All keyword arguments are passed to [ODSReader][msl.io.readers.ods.ODSReader].

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
            [Metadata][msl.io.metadata.Metadata].
    """
    file = os.fsdecode(file) if isinstance(file, (bytes, str, os.PathLike)) else str(file.name)
    with ODSReader(file, **kwargs) as ods:
        if cells is not None and not _spreadsheet_range_regex.match(cells):
            match = _spreadsheet_top_left_regex.match(cells)
            if not match:
                msg = f"Invalid cell {cells!r}"
                raise ValueError(msg)
            name = sheet or ods.sheet_names()[0]
            num_rows, num_columns = ods.dimensions(name)
            letters = ods.to_letters(num_columns - 1)
            cells += f":{letters}{num_rows}"
        table = ods.read(cells, sheet=sheet, as_datetime=as_datetime, merged=merged)
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

    if isinstance(dtype, str) and dtype.startswith("header"):
        dtype = _header_dtype(dtype, header)

    return Dataset(
        name=get_basename(file),
        parent=None,
        read_only=True,
        data=data,
        dtype=dtype,
        header=np.asarray(header, dtype=str),
    )


def read_table(file: PathLike | ReadLike, **kwargs: Any) -> Dataset:
    """Read data in a table format from a file.

    A *table* has the following properties:

    1. The first row is a header
    2. All rows have the same number of columns
    3. All data values in a column have the same data type

    !!! example "See the [Overview][read-a-table] for examples."

    Args:
        file: The file to read. If `file` is a Google Sheets spreadsheet then `file` must end
            with `.gsheet` even if the ID of the spreadsheet is specified.
        kwargs: If the file is an Excel spreadsheet then the keyword arguments are passed to
            [read_table_excel][msl.io.tables.read_table_excel]. If a Google Sheets spreadsheet then
            the keyword arguments are passed to [read_table_gsheets][msl.io.tables.read_table_gsheets].
            If an OpenDocument Spreadsheet then the keyword arguments are passed to
            [read_table_ods][msl.io.tables.read_table_ods]. Otherwise, all keyword arguments are
            passed to [read_table_text][msl.io.tables.read_table_text].

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included in the
            [Metadata][msl.io.metadata.Metadata].
    """
    ext = get_extension(file).lower()
    if ext in {".xls", ".xlsx"}:
        return read_table_excel(file, **kwargs)

    if ext in {".ods", ".fods"}:
        return read_table_ods(file, **kwargs)

    if ext == ".gsheet":
        file = os.fsdecode(file) if isinstance(file, (bytes, str, os.PathLike)) else str(file.name)
        return read_table_gsheets(file.removesuffix(".gsheet"), **kwargs)

    return read_table_text(file, **kwargs)
