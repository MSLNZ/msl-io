from datetime import date, datetime
from pathlib import Path

import pytest

from msl.io import ODSReader

samples = Path(__file__).parent / "samples"


def test_raises() -> None:
    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        _ = ODSReader("does not exist.ods")

    with pytest.raises(ValueError, match=r"Unsupported OpenDocument Spreadsheet"):
        _ = ODSReader(samples / "table.xls")

    # the sheet does not exist
    with pytest.raises(ValueError, match=r"A sheet named 'whatever' is not in"):
        _ = ODSReader(samples / "ods_datatypes.ods").read(sheet="whatever")

    # more than one sheet
    with pytest.raises(ValueError, match=r"You must specify the name of the sheet"):
        _ = ODSReader(samples / "table.ods").read()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("ods_datatypes.ods", ("Sheet1",)),
        ("ods_datatypes.fods", ("Sheet1",)),
        ("table.ods", ("A1", "BH11", "AEX154041")),
        ("lab_environment.ods", ("Lab Environment",)),
        ("repeats.ods", ("Ones", "Hidden", "Merged")),
    ],
)
def test_sheet_names(filename: str, expected: tuple[str, ...]) -> None:
    with ODSReader(samples / filename) as ods:
        assert ods.sheet_names() == expected


@pytest.mark.parametrize("ext", ["ods", "fods"])
def test_datatypes(ext: str) -> None:
    # the following file only contains 1 sheet, so we don't have to specify the sheet
    file = str(samples / f"ods_datatypes.{ext}")
    ods = ODSReader(file)
    assert ods.file == file
    assert ods.sheet_names() == ("Sheet1",)
    assert ods.read(as_datetime=False) == [
        (1.23, True, "09/13/2019 01:20 PM", "09/13/19"),
        (3.14159265358979, "some text", None, 0.34),
        ("3 ½", 9.99e99, "03:38:00 AM", None),
    ]
    assert ods.read(cell="A1") == 1.23  # $1.23
    assert ods.read(cell="B1") is True
    assert ods.read(cell="C1") == datetime(2019, 9, 13, 13, 20, 22)  # noqa: DTZ001
    assert ods.read(cell="C1", as_datetime=False) == "09/13/2019 01:20 PM"
    assert ods.read(cell="D1") == date(2019, 9, 13)
    assert ods.read(cell="D1", as_datetime=False) == "09/13/19"
    assert ods.read(cell="A2") == 3.14159265358979
    assert ods.read(cell="B2") == "some text"
    assert ods.read(cell="C2") is None
    assert ods.read(cell="D2") == 0.34  # 34%
    assert ods.read(cell="A3") == "3 ½"
    assert ods.read(cell="B3") == 9.99e99
    assert ods.read(cell="C3") == "03:38:00 AM"  # office:value-type="time" is treated as a string
    assert ods.read(cell="D3") is None
    assert ods.read(cell="A1:A2") == [(1.23,), (3.14159265358979,)]


def test_table() -> None:  # noqa: PLR0915
    file = str(samples / "table.ods")
    ods = ODSReader(file)
    values = [
        ("timestamp", "val1", "uncert1", "val2", "uncert2"),
        (datetime(2019, 9, 11, 14, 6, 55), -0.505382, 0.000077, 0.501073, 0.000079),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 6, 59), -0.505191, 0.000066, 0.500877, 0.000083),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 3), -0.505308, 0.000086, 0.500988, 0.000087),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 7), -0.505250, 0.000119, 0.500923, 0.000120),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 11), -0.505275, 0.000070, 0.500965, 0.000088),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 15), -0.505137, 0.000079, 0.500817, 0.000085),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 19), -0.505073, 0.000099, 0.500786, 0.000084),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 23), -0.505133, 0.000088, 0.500805, 0.000076),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 27), -0.505096, 0.000062, 0.500759, 0.000062),  # noqa: DTZ001
        (datetime(2019, 9, 11, 14, 7, 31), -0.505072, 0.000142, 0.500739, 0.000149),  # noqa: DTZ001
    ]

    assert ods.file == file
    assert ods.sheet_names() == ("A1", "BH11", "AEX154041")

    # single cell
    assert ods.read(cell="A1", sheet="A1") == "timestamp"
    assert ods.read(cell="B2", sheet="A1") == -0.505382
    assert ods.read(cell="C7", sheet="A1") == 0.000079
    assert ods.read(cell="A100", sheet="A1") is None  # A100 is empty (also out of bounds)
    assert ods.read(cell="BI12", sheet="BH11") == -0.505382
    assert ods.read(cell="A1", sheet="BH11") is None  # A1 is empty
    assert ods.read(cell="ZZ1000", sheet="BH11") is None  # ZZ1000 is empty (also out of bounds)
    assert ods.read(cell="AFB154045", sheet="AEX154041") == 0.00012
    assert ods.read(cell="AA25", sheet="AEX154041") is None  # AA25 is empty
    assert ods.read(cell="BAA200000", sheet="AEX154041") is None  # BAA200000 is empty (also out of bounds)

    # single row
    assert ods.read(cell="A1:E1", sheet="A1") == [values[0]]
    assert ods.read(cell="BH11:BL11", sheet="BH11") == [values[0]]
    assert ods.read(cell="A2:E2", sheet="A1") == [values[1]]
    assert ods.read(cell="BH12:BL12", sheet="BH11") == [values[1]]
    assert ods.read(cell="A3:E3", sheet="A1") == [values[2]]
    assert ods.read(cell="BH13:BL13", sheet="BH11") == [values[2]]
    assert ods.read(cell="A4:E4", sheet="A1") == [values[3]]
    assert ods.read(cell="BH14:BL14", sheet="BH11") == [values[3]]
    assert ods.read(cell="A5:E5", sheet="A1") == [values[4]]
    assert ods.read(cell="BH15:BL15", sheet="BH11") == [values[4]]
    assert ods.read(cell="A6:E6", sheet="A1") == [values[5]]
    assert ods.read(cell="BH16:BL16", sheet="BH11") == [values[5]]
    assert ods.read(cell="A7:E7", sheet="A1") == [values[6]]
    assert ods.read(cell="BH17:BL17", sheet="BH11") == [values[6]]
    assert ods.read(cell="A8:E8", sheet="A1") == [values[7]]
    assert ods.read(cell="BH18:BL18", sheet="BH11") == [values[7]]
    assert ods.read(cell="A9:E9", sheet="A1") == [values[8]]
    assert ods.read(cell="BH19:BL19", sheet="BH11") == [values[8]]
    assert ods.read(cell="A10:E10", sheet="A1") == [values[9]]
    assert ods.read(cell="BH20:BL20", sheet="BH11") == [values[9]]
    assert ods.read(cell="A11:E11", sheet="A1") == [values[10]]
    assert ods.read(cell="BH21:BL21", sheet="BH11") == [values[10]]
    assert ods.read(cell="A6:B6", sheet="A1") == [values[5][:2]]
    assert ods.read(cell="A12:C12", sheet="A1") == []  # row 12 is empty (also out of bounds)
    assert ods.read(cell="A1000:Z1000", sheet="A1") == []  # row 1000 is empty (also out of bounds)
    assert ods.read(cell="BH22:BL22", sheet="BH11") == []  # row 22 is empty (also out of bounds)
    assert ods.read(cell="A1000:ZZ1000", sheet="BH11") == []  # row 1000 is empty (also out of bounds)
    assert ods.read(cell="A1:A1", sheet="A1") == [("timestamp",)]
    assert ods.read(cell="D9:D9", sheet="A1") == [(0.500805,)]

    # single column
    assert ods.read(cell="A:A", sheet="A1") == [(item[0],) for item in values]
    assert ods.read(cell="B:B", sheet="A1") == [(item[1],) for item in values]
    assert ods.read(cell="C:C", sheet="A1") == [(item[2],) for item in values]
    assert ods.read(cell="D:D", sheet="A1") == [(item[3],) for item in values]
    assert ods.read(cell="E:E", sheet="A1") == [(item[4],) for item in values]
    assert ods.read(cell="F:F", sheet="A1") == []  # column F is empty (also out of bounds)
    assert ods.read(cell="ABC:ABC", sheet="A1") == []  # column ABC is empty (also out of bounds)
    assert ods.read(cell="BH:BH", sheet="BH11") == [(None,) for _ in range(10)] + [(item[0],) for item in values]
    assert ods.read(cell="A:A", sheet="BH11") == [(None,) for _ in range(21)]  # column A is empty
    assert ods.read(cell="BG:BG", sheet="BH11") == [(None,) for _ in range(21)]  # column BG is empty

    # 2D slices
    assert ods.read(cell="A:E", sheet="A1") == values
    assert ods.read(cell="A1:E11", sheet="A1") == values
    assert ods.read(cell="A1:AAA10000", sheet="A1") == values  # slicing out of range is okay
    assert ods.read(cell="A1:C6", sheet="A1") == [row[:3] for row in values[:6]]
    assert ods.read(cell="A10:E11", sheet="A1") == values[-2:]
    assert ods.read(cell="A10:E1000", sheet="A1") == values[-2:]  # slicing out of range is okay
    assert ods.read(cell="A:E", sheet="BH11") == [tuple(None for _ in range(5)) for _ in range(21)]
    new = [tuple(None for _ in range(6))]
    for row in values:
        new.append((None, *row))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # noqa: PERF401
    assert ods.read(cell="BG10:BM22", sheet="BH11") == new
    assert ods.read(cell="BK20:BL21", sheet="BH11") == [row[-2:] for row in values[-2:]]
    assert ods.read(cell="AEX154041:AFB154051", sheet="AEX154041") == values
    assert ods.read(cell="AEX154041:ZZZ1000000", sheet="AEX154041") == values  # slicing out of range is okay
    assert ods.read(cell="AEY154042:AFA154044", sheet="AEX154041") == [row[1:4] for row in values[1:4]]
    assert ods.read(cell="J1:M10", sheet="A1") == []


def test_repeats_ones() -> None:
    file = samples / "repeats.ods"
    ods = ODSReader(file)
    assert ods.file == str(file)
    assert ods.sheet_names() == ("Ones", "Hidden", "Merged")
    assert ods.read(sheet="Ones") == [
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0, 1.0),
    ]
    assert ods.read("A:A", sheet="Ones") == [(1.0,), (1.0,), (1.0,), (1.0,), (1.0,)]
    assert ods.read("A1:A5", sheet="Ones") == [(1.0,), (1.0,), (1.0,), (1.0,), (1.0,)]
    assert ods.read("A2:E2", sheet="Ones") == [(1.0, 1.0, 1.0, 1.0, 1.0)]
    assert ods.read("A1:Z1", sheet="Ones") == [(1.0, 1.0, 1.0, 1.0, 1.0)]
    assert ods.read("B3:D4", sheet="Ones") == [(1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
    assert ods.read("F1:Z10", sheet="Ones") == []


def test_repeats_hidden() -> None:
    file = samples / "repeats.ods"
    ods = ODSReader(file)
    assert ods.file == str(file)
    assert ods.sheet_names() == ("Ones", "Hidden", "Merged")
    assert ods.read(sheet="Hidden") == [
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, "a", "a", "a", "c", "c", None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None),
        (None, None, None, None, None, None, None, "c"),
    ]
    assert ods.read("C2:C7", sheet="Hidden") == [(None,), (None,), ("a",), (None,), (None,), (None,)]
    assert ods.read("F10:H10", sheet="Hidden") == [(None, None, "c")]
    assert ods.read("G4:H", sheet="Hidden") == [
        ("c", None),
        (None, None),
        (None, None),
        (None, None),
        (None, None),
        (None, None),
        (None, "c"),
    ]
    assert ods.read("J:M", sheet="Hidden") == []


def test_repeats_merged() -> None:
    file = samples / "repeats.ods"
    ods = ODSReader(file)
    assert ods.file == str(file)
    assert ods.sheet_names() == ("Ones", "Hidden", "Merged")

    with pytest.raises(ValueError, match=r"column-spanned cells"):
        _ = ods.read(sheet="Merged")
    with pytest.raises(ValueError, match=r"row-spanned cells"):
        _ = ods.read("A2:D4", sheet="Merged")


@pytest.mark.parametrize(
    ("filename", "sheet", "expected"),
    [
        ("ods_datatypes.ods", "Sheet1", (3, 4)),
        ("ods_datatypes.fods", "Sheet1", (3, 4)),
        ("table.ods", "A1", (11, 5)),
        ("table.ods", "BH11", (21, 64)),
        ("table.ods", "AEX154041", (154051, 834)),
        ("lab_environment.ods", "Lab Environment", (5, 2)),
        ("repeats.ods", "Ones", (5, 5)),
        ("repeats.ods", "Hidden", (10, 8)),
        ("repeats.ods", "Merged", (4, 4)),
    ],
)
def test_shape(filename: str, sheet: str, expected: tuple[int, int]) -> None:
    with ODSReader(samples / filename) as ods:
        assert ods.shape(sheet) == expected


def test_shape_raises() -> None:
    ods = ODSReader(samples / "ods_datatypes.ods")
    with pytest.raises(ValueError, match=r"A sheet named 'Nope' is not in"):
        _ = ods.shape("Nope")
