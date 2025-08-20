"""Custom [Reader][msl.io.base.Reader]s."""

from __future__ import annotations

from .detector_responsivity_system import DRSReader
from .excel import ExcelReader
from .gsheets import GSheetsReader
from .hdf5 import HDF5Reader
from .json_ import JSONReader
from .ods import ODSReader
from .spectro_trans_reader import RegularTransmittanceReader

__all__: list[str] = [
    "DRSReader",
    "ExcelReader",
    "GSheetsReader",
    "HDF5Reader",
    "JSONReader",
    "ODSReader",
    "RegularTransmittanceReader",
]
