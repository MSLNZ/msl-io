import os
import pathlib
import sys
from datetime import datetime
from io import BytesIO
from io import StringIO

import numpy as np
import pytest

from tests.helper import datasets_equal
from msl.io import read_table
from msl.io.tables import read_table_excel
from msl.io.tables import read_table_gsheets
from tests.test_google_api import skipif_no_gdrive_readonly
from tests.test_google_api import skipif_no_sheets_readonly

# the data in the Excel, CVS and TXT files that are tested contain the following
header = np.asarray(["timestamp", "val1", "uncert1", "val2", "uncert2"], dtype=str)
data = np.asarray([
    ("2019-09-11 14:06:55", -0.505382, 0.000077, 0.501073, 0.000079),
    ("2019-09-11 14:06:59", -0.505191, 0.000066, 0.500877, 0.000083),
    ("2019-09-11 14:07:03", -0.505308, 0.000086, 0.500988, 0.000087),
    ("2019-09-11 14:07:07", -0.505250, 0.000119, 0.500923, 0.000120),
    ("2019-09-11 14:07:11", -0.505275, 0.000070, 0.500965, 0.000088),
    ("2019-09-11 14:07:15", -0.505137, 0.000079, 0.500817, 0.000085),
    ("2019-09-11 14:07:19", -0.505073, 0.000099, 0.500786, 0.000084),
    ("2019-09-11 14:07:23", -0.505133, 0.000088, 0.500805, 0.000076),
    ("2019-09-11 14:07:27", -0.505096, 0.000062, 0.500759, 0.000062),
    ("2019-09-11 14:07:31", -0.505072, 0.000142, 0.500739, 0.000149),
], dtype="U19,f8,f8,f8,f8")

# the data in the GSheet spreadsheet
gsheet_header = np.asarray(["Timestamp", "Value", "Valid", "ID"])
gsheet_data = np.asarray([
    (datetime(2019, 9, 11, 14, 6, 55), 20.1, True, "sensor 1"),
    (datetime(2019, 9, 11, 14, 6, 59), 25.4, False, "sensor 2"),
    (datetime(2019, 9, 11, 14, 7, 3), 19.4, True, "sensor 3"),
    (datetime(2019, 9, 11, 14, 7, 7), 11.8, False, "sensor 4"),
    (datetime(2019, 9, 11, 14, 7, 11), 24.6, False, "sensor 5"),
    (datetime(2019, 9, 11, 14, 7, 15), 20.7, True, "sensor 1"),
    (datetime(2019, 9, 11, 14, 7, 19), 21.8, True, "sensor 2"),
    (datetime(2019, 9, 11, 14, 7, 23), 19.2, True, "sensor 3"),
    (datetime(2019, 9, 11, 14, 7, 27), 18.6, False, "sensor 4"),
    (datetime(2019, 9, 11, 14, 7, 31), 16.4, False, "sensor 5"),
])


INVALID_CELL_RANGES = ["", ":", "A", "A:", "1", "ZZ", "AB", "A-B", "A1D10", "A1-D10"]


def get_url(extension):
    return os.path.join(os.path.dirname(__file__), "samples", "table" + extension)


def test_raises():

    # file does not exist
    with pytest.raises(OSError):
        read_table("does not exist")

    # the 'unpack' argument is not supported for text-based files
    with pytest.raises(ValueError, match="unpack"):
        read_table(get_url(".csv"), unpack=True)

    # invalid cell range
    for c in INVALID_CELL_RANGES:
        with pytest.raises(ValueError, match=r"Invalid cell"):
            read_table(get_url(".xls"), cells=c, sheet="A1")


def test_excel_range_out_of_bounds():
    for c in ["A100", "J1:M10"]:
        dset = read_table(get_url(".xls"), cells=c, sheet="A1")
        assert dset.metadata.header.size == 0
        assert dset.size == 0

    dset = read_table(get_url(".xls"), cells="A1:Z100", sheet="A1", as_datetime=False, dtype=data.dtype)
    assert np.array_equal(dset.metadata.header, header)
    assert np.array_equal(dset.data, data)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(dtype=data.dtype)),
     (".txt", dict(dtype=data.dtype, delimiter="\t")),
     (".xls", dict(dtype=data.dtype, sheet="A1", as_datetime=False)),
     (".xls", dict(dtype=data.dtype, sheet="BH11", as_datetime=False, cells="BH11:BL21")),
     (".xlsx", dict(dtype=data.dtype, sheet="A1", as_datetime=False)),
     (".xlsx", dict(dtype=data.dtype, sheet="BH11", as_datetime=False, cells="BH11:BL21")),
     (".xlsx", dict(dtype=data.dtype, sheet="AEX154041", as_datetime=False, cells="AEX154041:AFB154051"))]
)
def test_fetch_all_data(extn, kwargs):
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, header)
    assert np.array_equal(dset.data, data)
    assert dset.shape == (10,)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(usecols=(1, 2, 3, 4))),
     (".txt", dict(usecols=(1, 2, 3, 4), delimiter="\t")),
     (".xls", dict(sheet="A1", cells="B1:E11")),
     (".xls", dict(sheet="BH11", cells="BI11:BL21")),
     (".xlsx", dict(sheet="A1", cells="B1:E11")),
     (".xlsx", dict(sheet="BH11", cells="BI11:BL21")),
     (".xlsx", dict(sheet="AEX154041", cells="AEY154041:AFB154051"))]
)
def test_ignore_timestamp_column(extn, kwargs):
    floats = np.asarray([[e["f1"], e["f2"], e["f3"], e["f4"]] for e in data])
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, header[1:])
    assert np.array_equal(dset.data, floats)
    assert dset.shape == (10, 4)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(usecols=1)),
     (".txt", dict(usecols=1, delimiter="\t")),
     (".xls", dict(sheet="A1", cells="B1:B11")),
     (".xls", dict(sheet="BH11", cells="BI11:BI21")),
     (".xlsx", dict(sheet="A1", cells="B1:B11")),
     (".xlsx", dict(sheet="BH11", cells="BI11:BI21")),
     (".xlsx", dict(sheet="AEX154041", cells="AEY154041:AEY154051"))]
)
def test_single_column(extn, kwargs):
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, [header[1]])
    assert np.array_equal(dset.data, data["f1"])
    assert dset.shape == (10,)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(dtype=data.dtype, max_rows=1)),
     (".txt", dict(dtype=data.dtype, max_rows=1, delimiter="\t")),
     (".xls", dict(dtype=data.dtype, sheet="A1", as_datetime=False, cells="A1:E2")),
     (".xls", dict(dtype=data.dtype, sheet="BH11", as_datetime=False, cells="BH11:BL12")),
     (".xlsx", dict(dtype=data.dtype, sheet="A1", as_datetime=False, cells="A1:E2")),
     (".xlsx", dict(dtype=data.dtype, sheet="BH11", as_datetime=False, cells="BH11:BL12")),
     (".xlsx", dict(dtype=data.dtype, sheet="AEX154041", as_datetime=False, cells="AEX154041:AFB154042"))]
)
def test_single_row(extn, kwargs):
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, header)
    assert np.array_equal(dset.data, data[0])


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".xls", dict(sheet="A1", cells="A1:E1")),
     (".xls", dict(sheet="BH11", cells="BH11:BL11")),
     (".xlsx", dict(sheet="A1", cells="A1:E1")),
     (".xlsx", dict(sheet="BH11", cells="BH11:BL11")),
     (".xlsx", dict(sheet="AEX154041", cells="AEX154041:AFB154041"))]
)
def test_header_only(extn, kwargs):
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, header)
    assert dset.data.size == 0


def to_datetime(string):
    return datetime.strptime(string.decode(), "%Y-%m-%d %H:%M:%S")


dt = {"names": header, "formats": [object, float, float, float, float]}


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(dtype=dt, converters={0: to_datetime}, encoding="bytes")),
     (".txt", dict(dtype=dt, converters={0: to_datetime}, delimiter="\t", encoding="bytes")),
     (".xls", dict(dtype=dt, sheet="A1")),
     (".xls", dict(dtype=dt, sheet="BH11", cells="BH11:BL21")),
     (".xlsx", dict(dtype=dt, sheet="A1")),
     (".xlsx", dict(dtype=dt, sheet="BH11", cells="BH11:BL21")),
     (".xlsx", dict(dtype=dt, sheet="AEX154041", cells="AEX154041:AFB154051"))]
)
def test_datetime_objects(extn, kwargs):
    datetimes = np.asarray([to_datetime(item.encode()) for item in data["f0"]], dtype=object)
    data_datetimes = np.asarray([
        (a, b, c, d, e) for a, b, c, d, e in zip(datetimes, data["f1"], data["f2"], data["f3"], data["f4"])
    ], dtype=dt)

    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, header)
    for h in header:
        assert np.array_equal(dset[h], data_datetimes[h])
    assert dset.shape == (10,)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(dtype=data.dtype, skiprows=5)),
     (".txt", dict(dtype=data.dtype, delimiter="\t", skiprows=5))]
)
def test_skip_rows_5(extn, kwargs):
    new_header = ["2019-09-11 14:07:11", "-0.505275", "0.000070", "0.500965", "0.000088"]
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, new_header)
    assert np.array_equal(dset.data, data[5:])
    assert dset.shape == (5,)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(skiprows=3, usecols=(1, 4))),
     (".txt", dict(skiprows=3, usecols=(1, 4), delimiter="\t"))]
)
def test_skip_rows_use_cols(extn, kwargs):
    h = ["-0.505308", "0.000087"]
    d = [[-0.505250, 0.000120],
         [-0.505275, 0.000088],
         [-0.505137, 0.000085],
         [-0.505073, 0.000084],
         [-0.505133, 0.000076],
         [-0.505096, 0.000062],
         [-0.505072, 0.000149]]
    dset = read_table(get_url(extn), **kwargs)
    assert np.array_equal(dset.metadata.header, h)
    assert np.array_equal(dset.data, d)
    assert dset.shape == (7, 2)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(skiprows=100)),
     (".txt", dict(skiprows=100))]
)
def test_skip_rows_100(extn, kwargs):
    dset = read_table(get_url(extn), **kwargs)
    assert dset.metadata.header.size == 0
    assert dset.size == 0


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".csv", dict(dtype=data.dtype, delimiter=",")),
     (".txt", dict(dtype=data.dtype, delimiter="\t"))]
)
def test_text_file_like(extn, kwargs):
    def assert_dataset(dataset):
        assert np.array_equal(dataset.metadata.header, header)
        assert np.array_equal(dataset.data, data)
        assert dataset.shape == (10,)

    # first, load it using the file path to get it into a Dataset object
    dset_temp = read_table(get_url(extn), **kwargs)

    with StringIO() as buf:
        delim = kwargs["delimiter"]
        buf.write(delim.join(h for h in dset_temp.metadata.header) + "\n")
        for row in dset_temp:
            buf.write(delim.join(str(val) for val in row) + "\n")

        buf.seek(0)
        dset = read_table(buf, **kwargs)
        assert dset.name == "StringIO"
        assert_dataset(dset)

    with open(get_url(extn), mode="rt") as fp:
        dset = read_table(fp, **kwargs)
        assert dset.name == "table" + extn
        assert_dataset(dset)

    kwargs["delimiter"] = kwargs["delimiter"].encode()

    with BytesIO() as buf:
        delim = kwargs["delimiter"]
        buf.write(delim.join(h.encode() for h in dset_temp.metadata.header) + b"\n")
        for row in dset_temp:
            buf.write(delim.join(str(val).encode() for val in row) + b"\n")

        buf.seek(0)
        dset = read_table(buf, **kwargs)
        assert dset.name == "BytesIO"
        assert_dataset(dset)

    with open(get_url(extn), mode="rb") as fp:
        dset = read_table(fp, **kwargs)
        assert dset.name == "table" + extn
        assert_dataset(dset)


@pytest.mark.parametrize(
    ("extn", "kwargs"),
    [(".xls", dict(dtype=data.dtype, sheet="A1", as_datetime=False)),
     (".xlsx", dict(dtype=data.dtype, sheet="A1", as_datetime=False))]
)
def test_excel_file_pointer(extn, kwargs):
    for mode in ["rt", "rb"]:
        with open(get_url(extn), mode=mode) as fp:
            dataset = read_table(fp, **kwargs)
            assert np.array_equal(dataset.metadata.header, header)
            assert np.array_equal(dataset.data, data)
            assert dataset.shape == (10,)
        with open(get_url(extn), mode=mode) as fp:
            dataset = read_table_excel(fp, **kwargs)
            assert np.array_equal(dataset.metadata.header, header)
            assert np.array_equal(dataset.data, data)
            assert dataset.shape == (10,)

    # there is no point to test StringIO nor BytesIO because `read_table`
    # checks the file path extension to decide how to read the table
    # and a StringIO and a BytesIO object do not have an extension to check
    # so read_table_excel will not be called, also xlrd cannot load a file stream


def test_pathlib():
    string = os.path.join(os.path.dirname(__file__), "samples", "table.csv")
    dset1 = read_table(string, dtype=object)
    dset2 = read_table(pathlib.Path(string), dtype=object)
    assert datasets_equal(dset1, dset2)

    string = os.path.join(os.path.dirname(__file__), "samples", "table.xls")
    dset1 = read_table(string, sheet="A1")
    dset2 = read_table(pathlib.Path(string), sheet="A1")
    assert datasets_equal(dset1, dset2)


@skipif_no_gdrive_readonly
@skipif_no_sheets_readonly
def test_gsheet_file_path():
    dset = read_table("table.gsheet", account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table("MSL/msl-io-testing/Copy of table.gsheet", account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)


@skipif_no_gdrive_readonly
@skipif_no_sheets_readonly
def test_gsheet_pathlib():
    dset = read_table(pathlib.Path("table.gsheet"), account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    path = pathlib.Path("MSL/msl-io-testing/Copy of table.gsheet")
    dset = read_table(path, account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table_gsheets(path, account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)


@skipif_no_gdrive_readonly
@skipif_no_sheets_readonly
def test_gsheet_file_pointer():
    filename = "table.gsheet"
    with open(filename, mode="w"):
        pass

    for m in ["rt", "rb"]:
        with open(filename, mode=m) as fp:
            dset = read_table(fp, account="testing", sheet="StartA1")
        assert np.array_equal(dset.metadata.header, gsheet_header)
        assert np.array_equal(dset, gsheet_data)

        with open(filename, mode=m) as fp:
            dset = read_table_gsheets(fp, account="testing", sheet="StartA1")
        assert np.array_equal(dset.metadata.header, gsheet_header)
        assert np.array_equal(dset, gsheet_data)

    os.remove(filename)

    # there is no point to test StringIO nor BytesIO because `read_table`
    # checks the file path extension to decide how to read the table
    # and a StringIO and a BytesIO object do not have an extension to check
    # so read_table_gsheets will not be called, also GSheets cannot load a file stream


@skipif_no_sheets_readonly
def test_gsheets_as_datetime():
    # ID of the table.gsheet file
    table_id = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"

    dset = read_table(table_id, account="testing", sheet="StartA1", as_datetime=False)
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset.data, gsheet_data.astype(str))

    dset = read_table(table_id, account="testing", sheet="StartA1", as_datetime=False, dtype=object)
    data2 = gsheet_data.copy()
    data2[:, 0] = [str(item) for item in gsheet_data[:, 0]]
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, data2)


@skipif_no_sheets_readonly
def test_gsheets_all_data():
    # ID of the table.gsheet file
    table_id = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ"

    dset = read_table(table_id+".gsheet", account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table_gsheets(table_id, account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(table_id+".gsheet", account="testing", sheet="StartH22")
    assert dset.metadata.header.size == 11
    assert dset.shape == (31, 11)
    for i in range(20):
        assert np.array_equal(dset[i], [None] * 11)
    assert np.array_equal(dset[20][:7], [None] * 7)
    assert np.array_equal(dset[20][7:], gsheet_header)
    for i, row in enumerate(gsheet_data, start=21):
        assert np.array_equal(dset[i][:7], [None] * 7)
        assert np.array_equal(dset[i][7:], row)

    dset = read_table(table_id+".gsheet", account="testing", sheet="StartH22", cells="H22")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    # ID of MSL/msl-io-testing/Copy of table.gsheet
    file = "1NfDUZzHk71CPAfhIoE8l9h4NJ8oeqKfqGAUM81Vyc88.gsheet"
    dset = read_table(file, account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)


@skipif_no_sheets_readonly
def test_gsheets_one_row():
    # ID of the table.gsheet file
    file = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"
    dset = read_table(file, account="testing", sheet="row")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data[0])


@skipif_no_sheets_readonly
def test_gsheets_one_column():
    # ID of the table.gsheet file
    file = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"
    dset = read_table(file, account="testing", sheet="column")
    assert np.array_equal(dset.metadata.header, [gsheet_header[1]])
    assert np.array_equal(dset, gsheet_data[:, 1])


@skipif_no_sheets_readonly
def test_gsheets_header_only():
    # ID of the table.gsheet file
    file = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"
    dset = read_table(file, account="testing", sheet="header only")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert dset.size == 0


@skipif_no_sheets_readonly
def test_gsheets_empty():
    # ID of the table.gsheet file
    file = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"
    dset = read_table(file, account="testing", sheet="empty")
    assert dset.metadata.header.size == 0
    assert dset.size == 0


@skipif_no_sheets_readonly
def test_gsheets_cell_range():
    # ID of the table.gsheet file
    file = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"

    dset = read_table(file, account="testing", sheet="StartH22", cells="H22")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(file, account="testing", sheet="StartH22", cells="H22:K32")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(file, account="testing", sheet="StartA1", cells="A1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(file, account="testing", sheet="StartA1", cells="A2")
    assert np.array_equal(dset.metadata.header, [str(item) for item in gsheet_data[0]])
    assert np.array_equal(dset, gsheet_data[1:])

    dset = read_table(file, account="testing", sheet="StartA1", cells="A4:C7")
    assert np.array_equal(dset.metadata.header, ["2019-09-11 14:07:03", "19.4", "True"])
    assert np.array_equal(dset, gsheet_data[3:6, :3])

    dset = read_table(file, account="testing", sheet="StartA1", cells="B1:B11")
    assert np.array_equal(dset.metadata.header, [gsheet_header[1]])
    assert np.array_equal(dset, gsheet_data[:, 1])

    dset = read_table(file, account="testing", sheet="StartA1", cells="A1:D2")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data[0])


@skipif_no_sheets_readonly
def test_gsheet_range_out_of_bounds():
    for c in ["A100", "J1:M10"]:
        dset = read_table("1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet",
                          cells=c, account="testing", sheet="StartA1")
        assert dset.metadata.header.size == 0
        assert dset.size == 0

    dset = read_table("1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet",
                      cells="A1:Z100", account="testing", sheet="StartA1")
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset.data, gsheet_data)


@skipif_no_sheets_readonly
def test_gsheet_raises():

    ssid = "1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet"

    # invalid cell range
    for c in INVALID_CELL_RANGES:
        with pytest.raises(ValueError, match=r"Invalid cell"):
            read_table(ssid, cells=c, sheet="StartA1", read_only=True, account="testing")
