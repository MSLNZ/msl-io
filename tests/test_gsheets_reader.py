# cSpell: ignore PSIQ Umvh Bfeme Agnw CEXTF Ecsh

from __future__ import annotations

from datetime import datetime

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import (  # type: ignore[import-untyped] # pyright: ignore[reportMissingTypeStubs]
    HttpError,  # pyright: ignore[reportUnknownVariableType]
)

from msl.io.google_api import GDrive
from msl.io.readers.gsheets import GSheetsReader, _google_file_id_regex  # pyright: ignore[reportPrivateUsage]

dr: GDrive | None
try:
    # dr -> drive, readonly
    dr = GDrive(account="testing", read_only=True)
except (OSError, RefreshError):
    dr = None

sr: GSheetsReader | None
try:
    # sr -> sheets, readonly
    sr = GSheetsReader("1TI3pM-534SZ5DQTEZ-7vCI04l48f8ZpLGbfEWJuCFSo", account="testing")
except (OSError, RefreshError):
    sr = None

skipif_no_gdrive_readonly = pytest.mark.skipif(dr is None, reason="No GDrive readonly token")

skipif_no_sheets_readonly = pytest.mark.skipif(sr is None, reason="No GSheets readonly token")


@skipif_no_sheets_readonly
def test_raises() -> None:
    table_gsheet_id = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"
    with pytest.raises(ValueError, match=r"You must specify the name of the sheet to read"):
        _ = GSheetsReader(table_gsheet_id, account="testing").read()

    table_gsheet_id = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"
    with pytest.raises(ValueError, match=r"There is no sheet named"):
        _ = GSheetsReader(table_gsheet_id, account="testing").read(sheet="A1")

    table_gsheet_id = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"
    with pytest.raises(HttpError):  # pyright: ignore[reportUnknownArgumentType]
        _ = GSheetsReader(table_gsheet_id, account="testing").read(sheet="SheetA1")


@skipif_no_sheets_readonly
def test_cell() -> None:
    # lab_environment.gsheet
    ssid = "1TI3pM-534SZ5DQTEZ-7vCI04l48f8ZpLGbfEWJuCFSo"
    values = [("temperature", "humidity"), (20.33, 49.82), (20.23, 46.06), (20.41, 47.06), (20.29, 48.32)]

    sheets = GSheetsReader(ssid, account="testing")
    assert sheets.file == ssid
    assert sheets.read() == values
    assert sheets.read(cell="A1") == "temperature"
    assert sheets.read(cell="A100") is None  # A100 is empty
    assert sheets.read(cell="B5") == 48.32  # noqa: PLR2004
    assert sheets.read(cell="A3:B3") == [(20.23, 46.06)]
    assert sheets.read(cell="A6:B6") == []  # row 6 is empty
    assert sheets.read(cell="B:B") == [("humidity",), (49.82,), (46.06,), (47.06,), (48.32,)]
    assert sheets.read(cell="C:C") == []  # column C is empty
    assert sheets.read(cell="A:B") == values
    assert sheets.read(cell="A1:B5") == values
    assert sheets.read(cell="A1:Z100") == values  # slicing out of range is okay
    assert sheets.read(cell="J1:M10") == []


@skipif_no_sheets_readonly
def test_sheet() -> None:
    # table.gsheet
    ssid = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"
    sheets = GSheetsReader(ssid, account="testing")
    assert sheets.file == ssid
    assert sheets.sheet_names() == ("StartA1", "StartH22", "header only", "empty", "column", "row")
    assert sheets.read(sheet="empty") == []
    assert sheets.read(sheet="header only") == [("Timestamp", "Value", "Valid", "ID")]
    assert sheets.read(sheet="column") == [
        ("Value",),
        (20.1,),
        (25.4,),
        (19.4,),
        (11.8,),
        (24.6,),
        (20.7,),
        (21.8,),
        (19.2,),
        (18.6,),
        (16.4,),
    ]
    assert sheets.read(sheet="row") == [
        ("Timestamp", "Value", "Valid", "ID"),
        (datetime(2019, 9, 11, 14, 6, 55), 20.1, True, "sensor 1"),  # noqa: DTZ001
    ]

    assert sheets.read("A1:A1", sheet="StartA1") == [("Timestamp",)]
    assert sheets.read("D9:D9", sheet="StartA1") == [("sensor 3",)]


@skipif_no_sheets_readonly
def test_as_datetime() -> None:
    # table.gsheet
    ssid = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"
    sheets = GSheetsReader(ssid, account="testing")
    assert sheets.read(cell="A:A", sheet="StartA1", as_datetime=True) == [
        ("Timestamp",),
        (datetime(2019, 9, 11, 14, 6, 55),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 6, 59),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 3),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 7),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 11),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 15),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 19),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 23),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 27),),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 31),),  # noqa: DTZ001
    ]
    assert sheets.read(cell="A:B", sheet="StartA1", as_datetime=False) == [
        ("Timestamp", "Value"),
        ("2019-09-11 14:06:55", 20.1),
        ("2019-09-11 14:06:59", 25.4),
        ("2019-09-11 14:07:03", 19.4),
        ("2019-09-11 14:07:07", 11.8),
        ("2019-09-11 14:07:11", 24.6),
        ("2019-09-11 14:07:15", 20.7),
        ("2019-09-11 14:07:19", 21.8),
        ("2019-09-11 14:07:23", 19.2),
        ("2019-09-11 14:07:27", 18.6),
        ("2019-09-11 14:07:31", 16.4),
    ]


@skipif_no_gdrive_readonly
@skipif_no_sheets_readonly
def test_file_path() -> None:
    path = "My Drive/MSL/msl-io-testing/empty-5.gsheet"
    sheets = GSheetsReader(path, account="testing")
    assert sheets.file == path
    assert sheets.sheet_names() == ("Sheet1", "Sheet2", "Sheet3", "Sheet4", "Sheet5")
    assert sheets.read(sheet="Sheet1") == []

    sheets = GSheetsReader("table", account="testing")
    assert sheets.file == "table"
    assert sheets.read(sheet="empty") == []


def test_google_file_id_regex() -> None:
    assert _google_file_id_regex.search("1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ")
    assert _google_file_id_regex.search("1IemLij3ggB_S5ASO7qyPSIQUmvhWgBfemePn7guAJe4")
    assert _google_file_id_regex.search("1IemLij3ggB-S5ASO7qyPSIQUmvhWgBfemePn7guAJe4")
    assert _google_file_id_regex.search("1IemL_j3ggB-S5ASO-qyPSIQUmv_WgBfe-ePn7gu-Je4")

    # does not start with 1
    assert not _google_file_id_regex.search("Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ1")

    # not 44 characters
    for n in [0, 10, 40, 42, 43, 45, 50, 100]:
        assert not _google_file_id_regex.search("1" * n)

    # contains an invalid character
    for c in r""" !"#$%&'()*+,./:;<=>?@[\]^`{|}~""":
        assert not _google_file_id_regex.search(f"1Q0TAgnw6AJQWkLMf{c}V3qEhEXuCEXTFAc95cEcshOXnQ")
