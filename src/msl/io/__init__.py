"""Read and write data files."""

from __future__ import annotations

from .__about__ import __author__, __copyright__, __version__, version_tuple
from .base import (
    Reader,
    Root,
    Writer,
    read,
    register,
)
from .google_api import GCellType, GDateTimeOption, GDrive, GMail, GSheets, GValueOption
from .node import Dataset, DatasetLogging, Group
from .readers import ExcelReader, GSheetsReader
from .tables import extension_delimiter_map, read_table
from .utils import (
    checksum,
    copy,
    git_head,
    is_admin,
    is_dir_accessible,
    is_file_readable,
    remove_write_permissions,
    run_as_admin,
    search,
    send_email,
)
from .writers import HDF5Writer, JSONWriter

__all__: list[str] = [
    "Dataset",
    "DatasetLogging",
    "ExcelReader",
    "GCellType",
    "GDateTimeOption",
    "GDrive",
    "GMail",
    "GSheets",
    "GSheetsReader",
    "GValueOption",
    "Group",
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
    "read",
    "read_table",
    "register",
    "remove_write_permissions",
    "run_as_admin",
    "search",
    "send_email",
    "version_tuple",
]
