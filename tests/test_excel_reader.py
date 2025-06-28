from datetime import date, datetime
from pathlib import Path

import pytest

from msl.io import ExcelReader
from msl.io.readers._xlrd import Book


def test_raises() -> None:
    file = Path(__file__).parent / "samples" / "table.xls"

    # file does not exist
    with pytest.raises(OSError, match=r"does not exist"):
        _ = ExcelReader("does not exist")

    # more than one sheet in the Excel workbook
    with pytest.raises(ValueError, match=r"You must specify the name of the sheet"):
        _ = ExcelReader(file).read()

    # the sheet does not exist in the Excel workbook
    with pytest.raises(ValueError, match=r"There is no sheet named"):
        _ = ExcelReader(file).read(sheet="XXXYYYZZZ")  # cSpell:ignore XXXYYYZZZ


def test_on_demand_default() -> None:
    file = Path(__file__).parent / "samples" / "table.xlsx"
    excel = ExcelReader(file)
    assert excel.workbook.on_demand is True


@pytest.mark.parametrize("on_demand", [True, False])
def test_cell(on_demand: bool) -> None:  # noqa: FBT001, PLR0915
    file = Path(__file__).parent / "samples" / "table.xlsx"
    excel = ExcelReader(file, on_demand=on_demand)
    assert excel.workbook.on_demand is on_demand
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

    assert excel.file == str(file)
    assert excel.sheet_names() == ("A1", "BH11", "AEX154041")
    assert isinstance(excel.workbook, Book)
    sheet = excel.workbook.sheet_by_name("A1")
    assert sheet.nrows == 11
    assert sheet.ncols == 5
    sheet = excel.workbook.sheet_by_name("BH11")
    assert sheet.nrows == 21
    assert sheet.ncols == 64
    sheet = excel.workbook.sheet_by_name("AEX154041")
    assert sheet.nrows == 154051
    assert sheet.ncols == 834

    # single cell
    assert excel.read(cell="A1", sheet="A1") == "timestamp"
    assert excel.read(cell="B2", sheet="A1") == -0.505382
    assert excel.read(cell="C7", sheet="A1") == 0.000079
    assert excel.read(cell="A100", sheet="A1") is None  # A100 is empty (also out of bounds)
    assert excel.read(cell="BI12", sheet="BH11") == -0.505382
    assert excel.read(cell="A1", sheet="BH11") is None  # A1 is empty
    assert excel.read(cell="ZZ1000", sheet="BH11") is None  # ZZ1000 is empty (also out of bounds)
    assert excel.read(cell="AFB154045", sheet="AEX154041") == 0.00012
    assert excel.read(cell="AA25", sheet="AEX154041") is None  # AA25 is empty
    assert excel.read(cell="BAA200000", sheet="AEX154041") is None  # BAA200000 is empty (also out of bounds)

    # single row
    assert excel.read(cell="A1:E1", sheet="A1") == [values[0]]
    assert excel.read(cell="BH11:BL11", sheet="BH11") == [values[0]]
    assert excel.read(cell="A2:E2", sheet="A1") == [values[1]]
    assert excel.read(cell="BH12:BL12", sheet="BH11") == [values[1]]
    assert excel.read(cell="A3:E3", sheet="A1") == [values[2]]
    assert excel.read(cell="BH13:BL13", sheet="BH11") == [values[2]]
    assert excel.read(cell="A4:E4", sheet="A1") == [values[3]]
    assert excel.read(cell="BH14:BL14", sheet="BH11") == [values[3]]
    assert excel.read(cell="A5:E5", sheet="A1") == [values[4]]
    assert excel.read(cell="BH15:BL15", sheet="BH11") == [values[4]]
    assert excel.read(cell="A6:E6", sheet="A1") == [values[5]]
    assert excel.read(cell="BH16:BL16", sheet="BH11") == [values[5]]
    assert excel.read(cell="A7:E7", sheet="A1") == [values[6]]
    assert excel.read(cell="BH17:BL17", sheet="BH11") == [values[6]]
    assert excel.read(cell="A8:E8", sheet="A1") == [values[7]]
    assert excel.read(cell="BH18:BL18", sheet="BH11") == [values[7]]
    assert excel.read(cell="A9:E9", sheet="A1") == [values[8]]
    assert excel.read(cell="BH19:BL19", sheet="BH11") == [values[8]]
    assert excel.read(cell="A10:E10", sheet="A1") == [values[9]]
    assert excel.read(cell="BH20:BL20", sheet="BH11") == [values[9]]
    assert excel.read(cell="A11:E11", sheet="A1") == [values[10]]
    assert excel.read(cell="BH21:BL21", sheet="BH11") == [values[10]]
    assert excel.read(cell="A6:B6", sheet="A1") == [values[5][:2]]
    assert excel.read(cell="A12:C12", sheet="A1") == []  # row 12 is empty (also out of bounds)
    assert excel.read(cell="A1000:Z1000", sheet="A1") == []  # row 1000 is empty (also out of bounds)
    assert excel.read(cell="BH22:BL22", sheet="BH11") == []  # row 22 is empty (also out of bounds)
    assert excel.read(cell="A1000:ZZ1000", sheet="BH11") == []  # row 1000 is empty (also out of bounds)
    assert excel.read(cell="A1:A1", sheet="A1") == [("timestamp",)]
    assert excel.read(cell="D9:D9", sheet="A1") == [(0.500805,)]

    # single column
    assert excel.read(cell="A:A", sheet="A1") == [(item[0],) for item in values]
    assert excel.read(cell="B:B", sheet="A1") == [(item[1],) for item in values]
    assert excel.read(cell="C:C", sheet="A1") == [(item[2],) for item in values]
    assert excel.read(cell="D:D", sheet="A1") == [(item[3],) for item in values]
    assert excel.read(cell="E:E", sheet="A1") == [(item[4],) for item in values]
    assert excel.read(cell="F:F", sheet="A1") == []  # column F is empty (also out of bounds)
    assert excel.read(cell="ABC:ABC", sheet="A1") == []  # column ABC is empty (also out of bounds)
    assert excel.read(cell="BH:BH", sheet="BH11") == [(None,) for _ in range(10)] + [(item[0],) for item in values]
    assert excel.read(cell="A:A", sheet="BH11") == [(None,) for _ in range(21)]  # column A is empty
    assert excel.read(cell="BG:BG", sheet="BH11") == [(None,) for _ in range(21)]  # column BG is empty

    # 2D slices
    assert excel.read(cell="A:E", sheet="A1") == values
    assert excel.read(cell="A1:E11", sheet="A1") == values
    assert excel.read(cell="A1:AAA10000", sheet="A1") == values  # slicing out of range is okay
    assert excel.read(cell="A1:C6", sheet="A1") == [row[:3] for row in values[:6]]
    assert excel.read(cell="A10:E11", sheet="A1") == values[-2:]
    assert excel.read(cell="A10:E1000", sheet="A1") == values[-2:]  # slicing out of range is okay
    assert excel.read(cell="A:E", sheet="BH11") == [tuple(None for _ in range(5)) for _ in range(21)]
    new = [tuple(None for _ in range(6))]
    for row in values:
        new.append((None, *row))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]  # noqa: PERF401
    assert excel.read(cell="BG10:BM22", sheet="BH11") == new
    assert excel.read(cell="BK20:BL21", sheet="BH11") == [row[-2:] for row in values[-2:]]
    assert excel.read(cell="AEX154041:AFB154051", sheet="AEX154041") == values
    assert excel.read(cell="AEX154041:ZZZ1000000", sheet="AEX154041") == values  # slicing out of range is okay
    assert excel.read(cell="AEY154042:AFA154044", sheet="AEX154041") == [row[1:4] for row in values[1:4]]
    assert excel.read(cell="J1:M10", sheet="A1") == []

    # calling close() multiple times is okay
    for _ in range(10):
        excel.close()


@pytest.mark.parametrize("on_demand", [True, False])
def test_datatypes(on_demand: bool) -> None:  # noqa: FBT001
    # the following workbook only contains 1 sheet, so we don't have to specify the sheet
    file = str(Path(__file__).parent / "samples" / "excel_datatypes.xlsx")
    excel = ExcelReader(file, on_demand=on_demand)
    assert excel.workbook.on_demand is on_demand
    assert excel.file == file
    assert excel.workbook.nsheets == 1
    assert excel.sheet_names() == ("Sheet1",)
    assert excel.read(cell="A1") == 1.23  # '$1.23'
    assert excel.read(cell="B1") is True
    assert excel.read(cell="C1") == datetime(2019, 9, 13, 13, 20, 22)  # noqa: DTZ001
    assert excel.read(cell="C1", as_datetime=False) == "2019-09-13 13:20:22"
    assert excel.read(cell="D1") == date(2019, 9, 13)
    assert excel.read(cell="D1", as_datetime=False) == "2019-09-13"
    assert excel.read(cell="A2") == 3.141592653589793
    assert excel.read(cell="B2") == "some text"
    assert excel.read(cell="C2") is None
    assert excel.read(cell="D2") == 0.34  # '34%'
    assert excel.read(cell="A1:A2") == [(1.23,), (3.141592653589793,)]

    # calling close() multiple times is okay
    for _ in range(10):
        excel.close()
