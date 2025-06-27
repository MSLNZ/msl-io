"""Read and write data files."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .__about__ import __author__, __copyright__, __version__, version_tuple
from .base import (
    Reader,
    Root,
    Writer,
    _readers,  # pyright: ignore[reportPrivateUsage]
    register,
)
from .google_api import GCellType, GDateTimeOption, GDrive, GMail, GSheets, GValueOption
from .readers import ExcelReader, GSheetsReader
from .tables import extension_delimiter_map, read_table_excel, read_table_gsheets, read_table_text
from .utils import (
    checksum,
    copy,
    git_head,
    is_admin,
    is_dir_accessible,
    is_file_readable,
    logger,
    remove_write_permissions,
    run_as_admin,
    search,
    send_email,
)
from .writers import HDF5Writer, JSONWriter

if TYPE_CHECKING:
    from typing import IO, Any

    from ._types import PathLike
    from .node import Dataset


__all__: list[str] = [
    "ExcelReader",
    "GCellType",
    "GDateTimeOption",
    "GDrive",
    "GMail",
    "GSheets",
    "GSheetsReader",
    "GValueOption",
    "HDF5Writer",
    "JSONWriter",
    "Reader",
    "Root",
    "Writer",
    "__about__",
    "__author__",
    "__copyright__",
    "__version__",
    "checksum",
    "copy",
    "extension_delimiter_map",
    "git_head",
    "is_admin",
    "is_dir_accessible",
    "is_file_readable",
    "register",
    "remove_write_permissions",
    "run_as_admin",
    "search",
    "send_email",
    "version_tuple",
]


def read(file: IO[bytes] | IO[str] | PathLike, **kwargs: Any) -> Reader:
    """Read a file that has a [Reader][io-readers] implemented.

    Args:
        file: The file to read.
        kwargs: All keyword arguments are passed to the [can_read][msl.io.base.Reader.can_read]
            and [read][msl.io.base.Reader.read] methods.

    Returns:
        The data from the file.
    """
    if isinstance(file, (bytes, str, os.PathLike)):
        file = os.fsdecode(file)
        readable = is_file_readable(file, strict=True)
    else:
        readable = hasattr(file, "read")

    if readable:
        logger.debug("finding Reader for %r", file)
        for r in _readers:
            logger.debug("checking %s", r.__name__)
            try:
                can_read = r.can_read(file, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.debug("%s: %s [%s]", e.__class__.__name__, e, r.__name__)
                continue

            if can_read:
                logger.debug("reading file with %s", r.__name__)
                root = r(file)
                root.read(**kwargs)
                root.read_only = True
                return root

    msg = f"No Reader exists to read {file!r}"
    raise OSError(msg)


def read_table(file: IO[bytes] | IO[str] | PathLike, **kwargs: Any) -> Dataset:
    """Read data in a table format from a file.

    A *table* has the following properties:

    1. The first row is a header.
    2. All rows have the same number of columns.
    3. All data values in a column have the same data type.

    Args:
        file: The file to read. If `file` is a Google Sheets spreadsheet then `file` must end
            with `.gsheet` even if the ID of the spreadsheet is specified.
        kwargs: If the file is an Excel spreadsheet then the keyword arguments are passed to
            [read_table_excel][msl.io.tables.read_table_excel]. If a Google Sheets spreadsheet then
            the keyword arguments are passed to [read_table_gsheets][msl.io.tables.read_table_gsheets].
            Otherwise, all keyword arguments are passed to [read_table_text][msl.io.tables.read_table_text].

    Returns:
        The table as a [Dataset][msl.io.node.Dataset]. The header is included as metadata.
    """
    ext = Reader.get_extension(file).lower()
    if ext.startswith(".xls"):
        return read_table_excel(file, **kwargs)

    if ext == ".gsheet":
        file = os.fsdecode(file) if isinstance(file, (bytes, str, os.PathLike)) else str(file.name)
        return read_table_gsheets(file.removesuffix(".gsheet"), **kwargs)

    return read_table_text(file, **kwargs)
