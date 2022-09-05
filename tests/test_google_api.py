import os
import io
import sys
import uuid
import tempfile
from datetime import datetime

import pytest
try:
    from googleapiclient.errors import HttpError
except ImportError:
    HttpError = Exception

from msl.io.constants import IS_PYTHON2
from msl.io.google_api import (
    GDrive,
    GSheets,
    GCell,
    GCellType,
    GValueOption,
    GMail,
)

# all Google API tests require the necessary "token.json" file to be
# available for a specific Google user's account
try:
    # dr -> drive, readonly
    dr = GDrive(account='testing', read_only=True)
except:
    dr = None

try:
    # dw -> drive, writable
    dw = GDrive(account='testing', read_only=False)
except:
    dw = None

try:
    # sr -> sheets, readonly
    sr = GSheets(account='testing', read_only=True)
except:
    sr = None

try:
    # sw -> sheets, writeable
    sw = GSheets(account='testing', read_only=False)
except:
    sw = None

try:
    gmail = GMail(account='testing')
except:
    gmail = None

skipif_no_gdrive_readonly = pytest.mark.skipif(
    dr is None, reason='No GDrive readonly token'
)

skipif_no_gdrive_writeable = pytest.mark.skipif(
    dw is None, reason='No GDrive writable token'
)

skipif_no_sheets_readonly = pytest.mark.skipif(
    sr is None, reason='No GSheets readonly token'
)

skipif_no_sheets_writeable = pytest.mark.skipif(
    sw is None, reason='No GSheets writeable token'
)

skipif_no_gmail = pytest.mark.skipif(
    gmail is None, reason='No Gmail token'
)

IS_WINDOWS = sys.platform == 'win32'


@skipif_no_sheets_readonly
def test_gsheets_sheet_names():
    # MSL/msl-io-testing/empty-5.gsheet
    names = sr.sheet_names('1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY')
    assert len(names) == 5
    assert 'Sheet1' in names
    assert 'Sheet2' in names
    assert 'Sheet3' in names
    assert 'Sheet4' in names
    assert 'Sheet5' in names

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment.gsheet
    names = sr.sheet_names('1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4')
    assert len(names) == 1
    assert 'Sensor_1' in names

    # table.gsheet
    names = sr.sheet_names('1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ')
    assert len(names) == 6
    assert 'StartA1' in names
    assert 'StartH22' in names
    assert 'header only' in names
    assert 'empty' in names
    assert 'column' in names
    assert 'row' in names


@skipif_no_sheets_readonly
def test_gsheets_values():
    # MSL/msl-io-testing/empty-5
    empty_id = '1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY'

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment
    lab_id = '1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4'

    # more than 1 sheet exists
    with pytest.raises(ValueError, match=r'You must specify a sheet name:'):
        sr.values(empty_id)

    # empty sheets are okay
    for name in sr.sheet_names(empty_id):
        values = sr.values(empty_id, sheet=name)
        assert isinstance(values, list)
        assert not values

        # specifying the cells in an empty sheet is okay
        values = sr.values(empty_id, sheet=name, cells='A2:Z10')
        assert isinstance(values, list)
        assert not values

    # only 1 sheet exists, therefore we do not need to specify
    # a value for the 'sheet' kwarg since it is determined automatically
    expected = [
        ['Timestamp', 'Temperature', 'Humidity'],
        ['2021-04-03 12:36:10', '20.33', '49.82'],
        ['2021-04-03 12:37:10', '20.23', '46.06'],
        ['2021-04-03 12:38:10', '20.41', '47.06'],
        ['2021-04-03 12:39:10', '20.29', '48.32']
    ]
    values = sr.values(lab_id)
    assert values == expected

    values = sr.values(lab_id, row_major=False)
    assert values == [
        ['Timestamp', '2021-04-03 12:36:10', '2021-04-03 12:37:10', '2021-04-03 12:38:10', '2021-04-03 12:39:10'],
        ['Temperature', '20.33', '20.23', '20.41', '20.29'],
        ['Humidity', '49.82', '46.06', '47.06', '48.32']
    ]

    values = sr.values(lab_id, cells='B2:C4', value_option='FORMATTED_VALUE')
    assert values == [['20.33', '49.82'], ['20.23', '46.06'], ['20.41', '47.06']]

    values = sr.values(lab_id, cells='B:B', value_option='UNFORMATTED_VALUE')
    assert values == [['Temperature'], [20.33], [20.23], [20.41], [20.29]]

    values = sr.values(lab_id, cells='B:C', value_option=GValueOption.UNFORMATTED)
    assert values == [['Temperature', 'Humidity'], [20.33, 49.82], [20.23, 46.06], [20.41, 47.06], [20.29, 48.32]]

    values = sr.values(lab_id, cells='A2:C2')
    assert values == [expected[1]]


@skipif_no_sheets_readonly
def test_gsheets_to_datetime():
    expected = [
        ['Timestamp', datetime(2021, 4, 3, 12, 36, 10), datetime(2021, 4, 3, 12, 37, 10),
         datetime(2021, 4, 3, 12, 38, 10), datetime(2021, 4, 3, 12, 39, 10)],
        ['Temperature', 20.33, 20.23, 20.41, 20.29],
        ['Humidity', 49.82, 46.06, 47.06, 48.32]
    ]

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment
    lab_id = '1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4'
    values = sr.values(lab_id, value_option='UNFORMATTED_VALUE', row_major=False)
    values[0][1:] = [sr.to_datetime(t) for t in values[0][1:]]
    assert values == expected

    values = sr.values(lab_id, value_option='UNFORMATTED_VALUE',
                       datetime_option='FORMATTED_STRING', row_major=False)
    expected[0][1:] = [str(t) for t in expected[0][1:]]
    assert values == expected


@skipif_no_sheets_readonly
def test_gsheets_cells():
    # MSL/msl-io-testing/empty-5
    empty_id = '1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY'

    # data-types
    datatypes_id = '1zMO4wk0IPC9I57dR5WoPTzlOX6g5-AcnwGFOEHrhIHU'

    # invalid spreadsheet_id
    with pytest.raises(HttpError):
        sr.cells(empty_id[:-1] + 'A')

    # valid spreadsheet_id, invalid sheet name
    with pytest.raises(HttpError):
        sr.cells(datatypes_id, ranges='invalid')
    with pytest.raises(HttpError):
        sr.cells(datatypes_id, ranges=['invalid'])

    assert sr.cells(empty_id) == {'Sheet1': [], 'Sheet2': [], 'Sheet3': [], 'Sheet4': [], 'Sheet5': []}

    assert sr.cells(empty_id, ranges='Sheet1') == {'Sheet1': []}
    assert sr.cells(empty_id, ranges=['Sheet1']) == {'Sheet1': []}
    assert sr.cells(empty_id, ranges=['Sheet1', 'Sheet5']) == {'Sheet1': [], 'Sheet5': []}
    assert sr.cells(empty_id, ranges=['Sheet1', 'Sheet3!B7:ZZ99']) == {'Sheet1': [], 'Sheet3': []}

    cells = sr.cells(datatypes_id)
    values = cells['Data Types']
    assert len(values) == 18

    assert len(values[0]) == 6
    assert values[0][0] == GCell(value='Automatic', type=GCellType.STRING, formatted='Automatic')
    assert values[0][1] == GCell(value=1.23, type=GCellType.NUMBER, formatted='1.23')
    assert values[0][2] == GCell(value='string', type=GCellType.STRING, formatted='string')
    assert values[0][3] == GCell(value=1, type=GCellType.NUMBER, formatted='1')
    assert values[0][4] == GCell(value='0123456789', type=GCellType.STRING, formatted='0123456789')
    assert values[0][5] == GCell(value=36982, type=GCellType.DATE, formatted='1 April 2001')

    assert len(values[1]) == 3
    assert values[1][0] == GCell(value='Plain text', type=GCellType.STRING, formatted='Plain text')
    assert values[1][1] == GCell(value='a b c d', type=GCellType.STRING, formatted='a b c d')
    assert values[1][2] == GCell(value='34', type=GCellType.STRING, formatted='34')

    assert len(values[2]) == 2
    assert values[2][0] == GCell(value='Number', type=GCellType.STRING, formatted='Number')
    assert values[2][1] == GCell(value=1234.56789, type=GCellType.NUMBER, formatted='1,234.57')

    assert len(values[3]) == 2
    assert values[3][0] == GCell(value='Percent', type=GCellType.STRING, formatted='Percent')
    assert values[3][1] == GCell(value=0.542, type=GCellType.PERCENT, formatted='54.20%')

    assert len(values[4]) == 2
    assert values[4][0] == GCell(value='Scientific', type=GCellType.STRING, formatted='Scientific')
    assert values[4][1] == GCell(value=0.00321, type=GCellType.SCIENTIFIC, formatted='3.21E-03')

    assert len(values[5]) == 3
    assert values[5][0] == GCell(value='Accounting', type=GCellType.STRING, formatted='Accounting')
    assert values[5][1] == GCell(value=99.95, type=GCellType.NUMBER, formatted=' $ 99.95 ')
    assert values[5][2] == GCell(value=-23.45, type=GCellType.NUMBER, formatted=' $ (23.45)')

    assert len(values[6]) == 3
    assert values[6][0] == GCell(value='Financial', type=GCellType.STRING, formatted='Financial')
    assert values[6][1] == GCell(value=1.23, type=GCellType.NUMBER, formatted='1.23')
    assert values[6][2] == GCell(value=-1.23, type=GCellType.NUMBER, formatted='(1.23)')

    assert len(values[7]) == 3
    assert values[7][0] == GCell(value='Currency', type=GCellType.STRING, formatted='Currency')
    assert values[7][1] == GCell(value=99.95, type=GCellType.CURRENCY, formatted='$99.95')
    assert values[7][2] == GCell(value=-1.99, type=GCellType.CURRENCY, formatted='-$1.99')

    assert len(values[8]) == 3
    assert values[8][0] == GCell(
        value='Currency (rounded)', type=GCellType.STRING, formatted='Currency (rounded)')
    assert values[8][1] == GCell(value=99.95, type=GCellType.CURRENCY, formatted='$100')
    assert values[8][2] == GCell(value=-1.99, type=GCellType.CURRENCY, formatted='-$2')

    assert len(values[9]) == 2
    assert values[9][0] == GCell(value='Date', type=GCellType.STRING, formatted='Date')
    assert values[9][1] == GCell(value=17738, type=GCellType.DATE, formatted='24/07/1948')

    assert len(values[10]) == 3
    assert values[10][0] == GCell(value='Time', type=GCellType.STRING, formatted='Time')
    assert values[10][1] == GCell(value=0.2661689814814815, type=GCellType.TIME, formatted='06:23:17')
    assert values[10][2] == GCell(value=0.7378356481481482, type=GCellType.TIME, formatted='17:42:29')

    assert len(values[11]) == 2
    assert values[11][0] == GCell(value='Date time', type=GCellType.STRING, formatted='Date time')
    assert values[11][1] == GCell(
        value=34736.4303472222222222, type=GCellType.DATE_TIME, formatted='06/02/1995 10:19:42')

    assert len(values[12]) == 2
    assert values[12][0] == GCell(value='Duration', type=GCellType.STRING, formatted='Duration')
    assert values[12][1] == GCell(value=1.000023148148148, type=GCellType.TIME, formatted='24:00:02')

    assert len(values[13]) == 2
    assert values[13][0] == GCell(value='Formula', type=GCellType.STRING, formatted='Formula')
    assert values[13][1] == GCell(value=6.747908247937978, type=GCellType.SCIENTIFIC, formatted='6.75E+00')

    assert len(values[14]) == 3
    assert values[14][0] == GCell(value='Error', type=GCellType.STRING, formatted='Error')
    assert values[14][1] == GCell(
        value='#DIV/0! (Function DIVIDE parameter 2 cannot be zero.)',
        type=GCellType.ERROR,
        formatted='#DIV/0!')
    assert values[14][2] == GCell(
        value="#VALUE! (Function MULTIPLY parameter 2 expects number values. "
              "But 'Currency' is a text and cannot be coerced to a number.)",
        type=GCellType.ERROR,
        formatted='#VALUE!')

    assert len(values[15]) == 3
    assert values[15][0] == GCell(value='Empty', type=GCellType.STRING, formatted='Empty')
    assert values[15][1] == GCell(value=None, type=GCellType.EMPTY, formatted='')
    assert values[15][2] == GCell(
        value='<== keep B16 empty', type=GCellType.STRING, formatted='<== keep B16 empty')

    assert len(values[16]) == 3
    assert values[16][0] == GCell(value='Boolean', type=GCellType.STRING, formatted='Boolean')
    assert values[16][1] == GCell(value=True, type=GCellType.BOOLEAN, formatted='TRUE')
    assert values[16][2] == GCell(value=False, type=GCellType.BOOLEAN, formatted='FALSE')

    assert len(values[17]) == 2
    assert values[17][0] == GCell(value='Custom', type=GCellType.STRING, formatted='Custom')
    assert values[17][1] == GCell(value=12345.6789, type=GCellType.NUMBER, formatted='12345 55/81')


@skipif_no_sheets_writeable
@skipif_no_gdrive_writeable
def test_gsheets_create_move_delete():
    sid = sw.create('no-sheet-names')
    assert sw.sheet_names(sid) == ('Sheet1',)
    dw.delete(sid)

    sid = sw.create('three-sheet-names', sheet_names=['a', 'bb', 'ccc'])
    assert dw.path(sid) == 'My Drive/three-sheet-names'
    assert sw.sheet_names(sid) == ('a', 'bb', 'ccc')
    fid = dw.create_folder('eat/more/fruit')
    dw.move(sid, fid)
    assert dw.path(sid) == 'My Drive/eat/more/fruit/three-sheet-names'
    dw.delete(dw.folder_id('My Drive/eat'))


@skipif_no_gdrive_readonly
def test_gdrive_shared_drives():
    assert dr.shared_drives() == {}


@skipif_no_gdrive_readonly
def test_gdrive_folder_id_exception():
    # the folder does not exist
    folders = [
        'DoesNotExist',
        '/Google Drive/MSL/DoesNotExist',
    ]
    if IS_WINDOWS:
        folders.append(r'C:\Users\username\Google Drive\MSL\DoesNotExist')
    for folder in folders:
        with pytest.raises(OSError, match=r'Not a valid Google Drive folder'):
            dr.folder_id(folder)

    # specified a valid file (which is not a folder)
    files = [
        'Single-Photon Generation and Detection.pdf',
        'MSL/msl-io-testing/unique'
    ]
    for file in files:
        with pytest.raises(OSError, match=r'Not a valid Google Drive folder'):
            dr.folder_id(file)

    # specify an invalid parent ID
    assert dr.folder_id('MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    with pytest.raises(HttpError):
        dr.folder_id('MSL', parent_id='INVALID_Kmkjo9aCQGysOsxwkTtpoJODi')


@skipif_no_gdrive_readonly
def test_gdrive_folder_id():
    # relative to the root folder
    assert dr.folder_id('') == 'root'
    assert dr.folder_id('/') == 'root'
    assert dr.folder_id('Google Drive') == 'root'
    if IS_WINDOWS:
        assert dr.folder_id('C:\\Users\\username\\Google Drive') == 'root'
        assert dr.folder_id(r'D:\Google Drive') == 'root'

    assert dr.folder_id('MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    assert dr.folder_id('MSL/msl-io-testing') == '1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C'
    assert dr.folder_id('MSL/msl-io-testing/f 1/f2') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert dr.folder_id('/Google Drive/MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    assert dr.folder_id('Google Drive/MSL/msl-io-testing/f 1') == '1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9'
    if IS_WINDOWS:
        assert dr.folder_id('C:\\Users\\username\\Google Drive\\MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
        assert dr.folder_id(r'MSL\msl-io-testing\f 1\f2\sub folder 3') == '1wLAPHCOphcOITR37b8UB88eFW_FzeNQB'

    # relative to a parent folder
    assert dr.folder_id('msl-io-testing', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C'
    assert dr.folder_id('msl-io-testing/f 1/f2', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert dr.folder_id('f 1/f2', parent_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert dr.folder_id('f2', parent_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert dr.folder_id('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN') == '1wLAPHCOphcOITR37b8UB88eFW_FzeNQB'


@skipif_no_gdrive_readonly
def test_gdrive_file_id_exception():
    # file does not exist
    files = [
        'DoesNotExist',
        '/home/username/Google Drive/DoesNotExist.txt',
    ]
    if IS_WINDOWS:
        files.append(r'C:\Users\username\Google Drive\DoesNotExist.txt')
    for file in files:
        with pytest.raises(OSError, match=r'Not a valid Google Drive file'):
            dr.file_id(file)

    # specified a valid folder (which is not a file)
    folders = [
        'MSL',
        '/Google Drive/MSL',
    ]
    if IS_WINDOWS:
        folders.append(r'C:\Users\username\Google Drive\MSL')
    for folder in folders:
        with pytest.raises(OSError, match=r'Not a valid Google Drive file'):
            dr.file_id(folder)

    # specify an invalid parent ID
    assert dr.file_id('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    with pytest.raises(HttpError):
        dr.file_id('unique', folder_id='INVALID_NCuTWxmABs-w7JenftaLGAG9C')


@skipif_no_gdrive_readonly
def test_gdrive_file_id():
    # relative to the root folder
    files = {
        'Single-Photon Generation and Detection.pdf': '11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS',
        'MSL/msl-io-testing/unique': '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395',
        '/Google Drive/Single-Photon Generation and Detection.pdf': '11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS',
    }
    if IS_WINDOWS:
        files[r'C:\Users\username\Google Drive\MSL\msl-io-testing\unique'] = '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
        files['MSL\\msl-io-testing\\f 1\\f2\\New Text Document.txt'] = '1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP'

    for file, id_ in files.items():
        assert dr.file_id(file) == id_

    # relative to a parent folder
    assert dr.file_id('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    assert dr.file_id('msl-io-testing/unique', folder_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    assert dr.file_id('file.txt', folder_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB') == '1CDS3cWDItXB1uLCPGq0uy6OJAngkmNoD'
    assert dr.file_id('f 1/f2/New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP'


@skipif_no_gdrive_readonly
def test_gdrive_file_id_multiple():
    # multiple files with the same name in the same folder
    path = 'MSL/msl-io-testing/f 1/electronics.xlsx'

    with pytest.raises(OSError) as err:
        dr.file_id(path)
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in str(err.value)
    assert GSheets.MIME_TYPE in str(err.value)

    mime_types = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '1aCSP8HU7mAz2hss8dP7IpNz0xJDzWSe1',
        GSheets.MIME_TYPE: '1SdLw6tlh4EaPeDis0pPepzYRBb_mx_i8fOwgODwQKaE',
    }
    for mime, id_ in mime_types.items():
        assert dr.file_id(path, mime_type=mime) == id_


@skipif_no_gdrive_readonly
@skipif_no_gdrive_writeable
def test_gdrive_create_delete_folder():

    # instantiated in read-only mode
    with pytest.raises(HttpError, match='Insufficient Permission'):
        dr.create_folder('TEST')

    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())

    # create (relative to root)
    for folder in [u1, u2 + '/sub-2/a b c']:
        folder_id = dw.create_folder(folder)
        assert dw.folder_id(folder) == folder_id

    # delete
    for folder in [u1, u2 + '/sub-2/a b c', u2 + '/sub-2', u2]:
        dw.delete(dw.folder_id(folder))
        with pytest.raises(OSError, match='Not a valid Google Drive folder'):
            dw.folder_id(folder)

    # create (relative to a parent folder)
    # ID of "MSL/msl-io-testing/f 1/f2/sub folder 3" is "1wLAPHCOphcOITR37b8UB88eFW_FzeNQB"
    u3 = str(uuid.uuid4())
    folder_id = dw.create_folder(u3 + '/a/b/c', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert dw.folder_id('MSL/msl-io-testing/f 1/f2/sub folder 3/' + u3 + '/a/b/c') == folder_id

    # these should not raise an error (do not need to assert anything)
    u3_id = dw.folder_id(u3, parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    u3_a_id = dw.folder_id('a', parent_id=u3_id)
    u3_a_b_id = dw.folder_id('b', parent_id=u3_a_id)
    u3_a_b_c_id = dw.folder_id('c', parent_id=u3_a_b_id)

    # deleting a folder should also delete the children folders
    dw.delete(u3_id)
    assert dw.is_folder('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert not dw.is_folder(u3 + '/a/b/c', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not dw.is_folder(u3 + '/a/b', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not dw.is_folder(u3 + '/a', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not dw.is_folder(u3, parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')

    # create multiple folders with the same name, check exists
    id1 = dw.create_folder('Temporary')
    id2 = dw.create_folder('Temporary')
    assert dw.path(id1) == 'My Drive/Temporary'
    assert dw.path(id2) == 'My Drive/Temporary'
    assert id1 != id2
    assert dw.is_folder('Temporary') is True
    with pytest.raises(OSError, match='^Multiple folders'):
        dw.folder_id('Temporary')
    dw.delete(id1)
    dw.delete(id2)


@skipif_no_gdrive_readonly
def test_gdrive_is_file():
    # relative to the root folder
    assert not dr.is_file('doesnotexist.txt')
    assert not dr.is_file('does/not/exist.txt')
    assert not dr.is_file('MSL')
    assert dr.is_file('MSL/msl-io-testing/unique')
    assert dr.is_file('MSL/msl-io-testing/f 1/electronics.xlsx')
    assert dr.is_file('MSL/msl-io-testing/f 1/electronics.xlsx', mime_type=GSheets.MIME_TYPE)
    if IS_WINDOWS:
        assert not dr.is_file('C:\\Users\\username\\Google Drive\\MSL\\msl-io-testing\\f 1')
        assert dr.is_file(r'MSL\msl-io-testing\f 1\f2\New Text Document.txt')

    # relative to a parent folder
    assert dr.is_file('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')
    assert dr.is_file('msl-io-testing/unique', folder_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi')
    assert dr.is_file('Single-Photon Generation and Detection.pdf', folder_id='root')
    assert dr.is_file('f 1/f2/New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')
    assert not dr.is_file('f2', folder_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9')
    assert not dr.is_file('New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')

    # relative to an invalid parent folder
    with pytest.raises(HttpError):
        dr.is_file('unique', folder_id='INVALID_NCuTWxmABs-w7JenftaLGAG9C')


@skipif_no_sheets_writeable
@skipif_no_gdrive_writeable
def test_gsheets_append():
    sid = sw.create('appending')
    sw.append(None, sid)
    sw.append([], sid)
    sw.append([[]], sid)
    sw.append(0, sid)
    sw.append([1, 2], sid, sheet='Sheet1')
    sw.append([[3, 4, 5, 6], [7, 8, 9]], sid)
    sw.append([[10, 11, 12, 13], [14, 15, 16]], sid, row_major=False)
    sw.append([None, 17], sid)
    assert sw.values(sid) == [
        ['0'],
        ['1', '2'],
        ['3', '4', '5', '6'],
        ['7', '8', '9'],
        ['10', '14'],
        ['11', '15'],
        ['12', '16'],
        ['13'],
        ['', '17']
    ]
    dw.delete(sid)

    sid = sw.create('appending-2', sheet_names=['Appender'])
    sw.append(['a', 'b', 'c'], sid)
    sw.append(['d', 'e', 'f', 'g'], sid, cell='D4')
    sw.append('h', sid, sheet='Appender')
    sw.append([['i', 'j'], ['k', 'l']], sid, cell='B7')
    sw.append([['m', 'n', 'o'], ['p', 'q', 'r']], sid, row_major=False, cell='A13')
    sw.append('s', sid, cell='A1')
    assert sw.values(sid) == [
        ['a', 'b', 'c'],
        ['s'],
        [],
        [],
        ['', '', '', 'd', 'e', 'f', 'g'],
        ['', '', '', 'h'],
        [],
        ['', 'i', 'j'],
        ['', 'k', 'l'],
        [],
        [],
        [],
        [],
        ['m', 'p'],
        ['n', 'q'],
        ['o', 'r']
    ]
    dw.delete(sid)


@skipif_no_sheets_writeable
@skipif_no_gdrive_writeable
def test_gsheets_write():
    sid = sw.create('writing')
    sw.write(None, sid, 'A1')
    sw.write([], sid, 'A1')
    sw.write([[]], sid, 'A1')
    sw.write(0, sid, 'C1')
    sw.write([1, 2], sid, 'A2:B3', sheet='Sheet1')
    sw.write([[3, 4, 5, 6], [7, 8, 9, 10], [11, 12, 13, 14]], sid, 'A4', row_major=False)
    assert sw.values(sid) == [
        ['', '', '0'],
        ['1', '2'],
        [],
        ['3', '7', '11'],
        ['4', '8', '12'],
        ['5', '9', '13'],
        ['6', '10', '14'],
    ]

    values = [list(range(10)), list(range(10, 20)), list(range(20, 30)), list(range(30, 40))]
    sw.write(values, sid, 'A2')
    expected = [['', '', 0]]
    expected.extend(values)
    expected.extend([[5, 9, 13], [6, 10, 14]])
    assert sw.values(sid, value_option=GValueOption.UNFORMATTED, sheet='Sheet1') == expected

    dw.delete(sid)


@skipif_no_sheets_writeable
@skipif_no_gdrive_writeable
def test_gsheets_copy_rename_add_delete():
    id1 = sw.create('spreadsheet1', sheet_names=['a', 'b', 'c'])
    id2 = sw.create('spreadsheet2')

    d_sheet = sw.add_sheets('d', id1)
    assert list(d_sheet.values()) == ['d']
    sheets = sw.add_sheets(['e', 'f', 'g'], id1)
    assert list(sheets.values()) == ['e', 'f', 'g']
    assert sw.sheet_names(id1) == ('a', 'b', 'c', 'd', 'e', 'f', 'g')

    assert sw.sheet_names(id2) == ('Sheet1',)
    bid = sw.copy('b', id1, id2)
    assert sw.sheet_names(id2) == ('Sheet1', 'Copy of b')
    sw.copy(list(d_sheet.keys())[0], id1, id2)
    assert sw.sheet_names(id2) == ('Sheet1', 'Copy of b', 'Copy of d')

    sw.rename_sheet(bid, 'B - B', id2)
    assert sw.sheet_names(id2) == ('Sheet1', 'B - B', 'Copy of d')

    sw.rename_sheet('a', 'different', id1)
    assert sw.sheet_names(id1) == ('different', 'b', 'c', 'd', 'e', 'f', 'g')

    sw.delete_sheets('different', id1)
    assert sw.sheet_names(id1) == ('b', 'c', 'd', 'e', 'f', 'g')
    sw.delete_sheets(bid, id2)
    assert sw.sheet_names(id2) == ('Sheet1', 'Copy of d')
    sw.delete_sheets(['g', list(d_sheet.keys())[0]], id1)
    assert sw.sheet_names(id1) == ('b', 'c', 'e', 'f')

    with pytest.raises(ValueError, match="no sheet named 'invalid'"):
        sw.copy('invalid', id1, id2)

    with pytest.raises(ValueError, match="no sheet named 'invalid'"):
        sw.delete_sheets('invalid', id1)

    # cleanup
    dw.delete(id1)
    dw.delete(id2)


@skipif_no_gdrive_readonly
def test_gdrive_is_folder():
    # relative to the root folder
    assert not dr.is_folder('doesnotexist')
    assert not dr.is_folder('MSL/msl-io-testing/unique')
    assert dr.is_folder('MSL')
    assert dr.is_folder('MSL/msl-io-testing/f 1/f2/sub folder 3')
    if IS_WINDOWS:
        assert not dr.is_folder('MSL\\msl-io-testing\\f 1\\electronics.xlsx')
        assert dr.is_folder(r'MSL\msl-io-testing\f 1')

    # relative to a parent folder
    assert not dr.is_folder('doesnotexist', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert not dr.is_folder('sub folder 3xx', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert dr.is_folder('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert dr.is_folder('f2', parent_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9')
    assert dr.is_folder('msl-io-testing/f 1/f2', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi')

    # relative to an invalid parent folder
    with pytest.raises(HttpError):
        dr.is_folder('f2', parent_id='INVALID_F5AhbUb7Lq77qzuBbvZr150X9')


@skipif_no_gdrive_readonly
@skipif_no_gdrive_writeable
def test_gdrive_upload():
    temp_file = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + '.py')
    with open(temp_file, mode='wt') as fp:
        fp.write('from msl.io import GDrive')

    # instantiated in read-only mode
    with pytest.raises(HttpError, match='Insufficient Permission'):
        dr.upload(temp_file)

    file_id = dw.upload(
        temp_file,
        folder_id=dw.folder_id('MSL'),
        mime_type='text/x-python'
    )

    path = os.path.join('MSL', os.path.basename(temp_file))
    assert dw.file_id(path, mime_type='text/x-python') == file_id
    assert dw.file_id(path) == file_id
    assert not dw.is_file(path, mime_type='application/x-python-code')

    dw.delete(file_id)
    assert not dw.is_file(path)
    os.remove(temp_file)


@skipif_no_gdrive_readonly
def test_gdrive_download():
    temp_file = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))

    file_id = dr.file_id('MSL/msl-io-testing/file.txt')

    # cannot be a string IO object
    with pytest.raises(TypeError):
        dr.download(file_id, save_to=io.StringIO())
    if not IS_PYTHON2:  # in Python 2, str and bytes are the same
        with pytest.raises(TypeError):
            dr.download(file_id, save_to=open('junk.txt', mode='wt'))
        os.remove('junk.txt')  # clean up since it got created before the error was raised

    # a BytesIO object
    with io.BytesIO() as buffer:
        dr.download(file_id, save_to=buffer)
        buffer.seek(0)
        assert buffer.read() == b'in "msl-io-testing"'

    # a file handle in 'wb' mode
    with open(temp_file, mode='wb') as fp:
        dr.download(file_id, save_to=fp)
    with open(temp_file, mode='rt') as fp:
        assert fp.read() == 'in "msl-io-testing"'
    os.remove(temp_file)  # clean up

    # do not specify a value for the 'save_to' kwarg
    # therefore the filename is determined from the remote filename
    # and saved to the current working directory
    file_id = dr.file_id('MSL/msl-io-testing/f 1/f2/sub folder 3/file.txt')
    dr.download(file_id)
    with open('file.txt', mode='rt') as fp:
        assert fp.read() == 'in "sub folder 3"'
    os.remove('file.txt')  # clean up

    # save to a specific directory, use the remote filename
    f = os.path.join(tempfile.gettempdir(), 'file.txt')
    if os.path.isfile(f):
        os.remove(f)
    assert not os.path.isfile(f)
    dr.download(file_id, save_to=tempfile.gettempdir())
    with open(f, mode='rt') as fp:
        assert fp.read() == 'in "sub folder 3"'
    os.remove(f)  # clean up

    # save to a specific file
    assert not os.path.isfile(temp_file)
    dr.download(file_id, save_to=temp_file)
    with open(temp_file, mode='rb') as fp:
        assert fp.read() == b'in "sub folder 3"'
    os.remove(temp_file)  # clean up

    # use a callback
    def handler(file):
        assert file.progress() == 1.0
        assert file.total_size == 17
        assert file.resumable_progress == 17
    dr.download(file_id, save_to=temp_file, callback=handler)
    os.remove(temp_file)  # clean up


@skipif_no_gdrive_readonly
@skipif_no_gdrive_writeable
def test_gdrive_empty_trash():
    # instantiated in read-only mode
    with pytest.raises(HttpError, match='Insufficient Permission'):
        dr.empty_trash()
    dw.empty_trash()


@skipif_no_gdrive_readonly
def test_gdrive_path():
    assert dr.path('0AFP6574OTgaaUk9PVA') == 'My Drive'
    assert dr.path('11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS') == 'My Drive/Single-Photon Generation and Detection.pdf'
    assert dr.path('14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == 'My Drive/MSL'
    assert dr.path('1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == 'My Drive/MSL/msl-io-testing'
    assert dr.path('1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY') == 'My Drive/MSL/msl-io-testing/empty-5'
    assert dr.path('1HG_emhGXBGaR7oS6ftioJOF-xbl1kv41') == 'My Drive/MSL/msl-io-testing/file.txt'
    assert dr.path('1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395') == 'My Drive/MSL/msl-io-testing/unique'
    assert dr.path('1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9') == 'My Drive/MSL/msl-io-testing/f 1'
    assert dr.path('1SdLw6tlh4EaPeDis0pPepzYRBb_mx_i8fOwgODwQKaE') == 'My Drive/MSL/msl-io-testing/f 1/electronics.xlsx'
    assert dr.path('1aCSP8HU7mAz2hss8dP7IpNz0xJDzWSe1') == 'My Drive/MSL/msl-io-testing/f 1/electronics.xlsx'
    assert dr.path('1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN') == 'My Drive/MSL/msl-io-testing/f 1/f2'
    assert dr.path('1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP') == 'My Drive/MSL/msl-io-testing/f 1/f2/New Text Document.txt'
    assert dr.path('1wLAPHCOphcOITR37b8UB88eFW_FzeNQB') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3'
    assert dr.path('1CDS3cWDItXB1uLCPGq0uy6OJAngkmNoD') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3/file.txt'
    assert dr.path('1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment'


@skipif_no_gdrive_writeable
def test_gdrive_copy():
    msl_io_testing_id = '1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C'
    assert dw.path(msl_io_testing_id) == 'My Drive/MSL/msl-io-testing'

    file_txt_id = '1HG_emhGXBGaR7oS6ftioJOF-xbl1kv41'
    assert dw.path(file_txt_id) == 'My Drive/MSL/msl-io-testing/file.txt'

    f2_id = '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert dw.path(f2_id) == 'My Drive/MSL/msl-io-testing/f 1/f2'

    # copy to the same folder (do not specify the destination folder)
    cid = dw.copy(file_txt_id)
    assert cid != file_txt_id
    assert dw.path(cid) == 'My Drive/MSL/msl-io-testing/file.txt'
    with pytest.raises(OSError, match='^Multiple files'):
        dw.file_id('file.txt', folder_id=msl_io_testing_id)
    assert dw.is_file('file.txt', folder_id=msl_io_testing_id) is True
    dw.delete(cid)
    assert dw.is_file('file.txt', folder_id=msl_io_testing_id)

    # copy to a different folder
    cid = dw.copy(file_txt_id, f2_id)
    assert cid != file_txt_id
    assert dw.path(cid) == 'My Drive/MSL/msl-io-testing/f 1/f2/file.txt'
    dw.delete(cid)
    assert dw.is_file('file.txt', folder_id=msl_io_testing_id)

    # copy to the same folder (but specify it) and rename
    cid = dw.copy(file_txt_id, msl_io_testing_id, name='new-file.dat')
    assert cid != file_txt_id
    assert dw.path(cid) == 'My Drive/MSL/msl-io-testing/new-file.dat'
    dw.delete(cid)
    assert not dw.is_file('new-file.dat', folder_id=msl_io_testing_id)
    assert dw.is_file('file.txt', folder_id=msl_io_testing_id)

    # copy to a different folder and rename (do not specify an extension)
    cid = dw.copy(file_txt_id, f2_id, name='abc')
    assert cid != file_txt_id
    assert dw.path(cid) == 'My Drive/MSL/msl-io-testing/f 1/f2/abc'
    dw.delete(cid)
    assert not dw.is_file('abc', folder_id=f2_id)
    assert dw.is_file('file.txt', folder_id=msl_io_testing_id)


@skipif_no_gdrive_writeable
def test_gdrive_rename():
    # rename a folder
    fid = dw.create_folder('My Folder')
    assert dw.path(fid) == 'My Drive/My Folder'
    dw.rename(fid, 'Renamed Folder')
    assert dw.path(fid) == 'My Drive/Renamed Folder'

    # rename a file
    file_txt_id = '1HG_emhGXBGaR7oS6ftioJOF-xbl1kv41'
    assert dw.path(file_txt_id) == 'My Drive/MSL/msl-io-testing/file.txt'
    cid = dw.copy(file_txt_id, fid)
    assert dw.path(cid) == 'My Drive/Renamed Folder/file.txt'
    dw.rename(cid, 'renamed file.txt')
    assert dw.path(cid) == 'My Drive/Renamed Folder/renamed file.txt'

    # cleanup
    dw.delete(fid)


@skipif_no_gdrive_writeable
def test_gdrive_move():
    # move a folder
    fid = dw.create_folder('X/Y/Z')
    assert dw.path(fid) == 'My Drive/X/Y/Z'
    dw.move(fid, 'root')
    assert dw.path(fid) == 'My Drive/Z'
    dw.move(fid, dw.folder_id('My Drive/X'))
    assert dw.path(fid) == 'My Drive/X/Z'

    # move a file (first create a copy)
    cid = dw.copy(dw.file_id('MSL/msl-io-testing/file.txt'), folder_id='root', name='copied.txt')
    assert dw.path(cid) == 'My Drive/copied.txt'
    dw.move(cid, fid)
    assert dw.path(cid) == 'My Drive/X/Z/copied.txt'

    # cleanup
    dw.delete(dw.folder_id('X'))


@skipif_no_gmail
def test_gmail_profile():
    profile = gmail.profile()
    assert profile['email_address'].endswith('@gmail.com')
    assert profile['messages_total'] > 1
    assert profile['threads_total'] > 1
    if IS_PYTHON2:
        assert isinstance(profile['history_id'], unicode)
    else:
        assert isinstance(profile['history_id'], str)
