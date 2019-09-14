import os
from datetime import datetime

import pytest
import xlrd

from msl.io import ExcelReader


def test_raises():

    url = os.path.join(os.path.dirname(__file__), 'samples', 'table.xls')

    # file does not exist
    with pytest.raises(IOError):
        ExcelReader('does not exist')

    # more than one sheet in the Excel workbook
    with pytest.raises(IOError) as e:
        ExcelReader(url).read()
    assert 'A1, BH11' in str(e.value)

    # the sheet does not exist in the Excel workbook
    with pytest.raises(ValueError) as e:
        ExcelReader(url).read(sheet='XXXYYYZZZ')
    assert 'XXXYYYZZZ' in str(e.value)

    # the cell range is invalid
    with pytest.raises(Exception) as e:
        ExcelReader(url).read(cell='A-B', sheet='A1')
    assert 'Unexpected character' in str(e.value)

    with pytest.raises(IndexError):
        ExcelReader(url).read(cell='AH42', sheet='A1')


def test_read():
    # NOTE: Reading a range of cells is tested in test_read_table.py

    url = os.path.join(os.path.dirname(__file__), 'samples', 'table.xlsx')
    excel = ExcelReader(url)
    assert excel.url == url
    assert isinstance(excel.workbook, xlrd.book.Book)
    assert excel.read(cell='A1', sheet='A1') == 'timestamp'
    assert excel.read(cell='A7', sheet='A1') == datetime(2019, 9, 11, 14, 7, 15)
    assert excel.read(cell='A7', sheet='A1', as_datetime=False) == '2019-09-11 14:07:15'
    assert excel.read(cell='B2', sheet='A1') == -0.505382
    assert excel.read(cell='AFB154045', sheet='AEX154041') == 0.00012
    assert excel.read(cell='A1', sheet='BH11') is None

    # check that calling close() multiple times is okay (on_demand is True by default)
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()

    # the following workbook only contains 1 sheet so we don't have to specify the sheet
    url = os.path.join(os.path.dirname(__file__), 'samples', 'excel_datatypes.xlsx')
    excel = ExcelReader(url, on_demand=False)
    assert excel.url == url
    assert excel.workbook.nsheets == 1
    assert excel.workbook.sheet_names()[0] == 'Sheet1'
    assert excel.read(cell='A1') == 1.23  # '$1.23' -> currency is just a number
    assert excel.read(cell='B1') is True
    assert excel.read(cell='C1') == datetime(2019, 9, 13, 13, 20, 22)
    assert excel.read(cell='C1', as_datetime=False) == '2019-09-13 13:20:22'
    assert excel.read(cell='A2') == 3.141592653589793
    assert excel.read(cell='B2') == 'some text'
    assert excel.read(cell='C2') is None
    assert excel.read(cell='A1:A2') == (1.23, 3.141592653589793)

    # check that calling close() multiple times is okay when on_demand=False
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
    excel.close()
