import os
import io
import sys
import tempfile
from datetime import datetime

import pytest
try:
    from googleapiclient.errors import HttpError
except ImportError:
    HttpError = Exception

from msl.io.constants import IS_PYTHON2
from msl.io import (
    GDrive,
    GSheets,
)

# all Google API tests require the necessary "token.json" files to be
# available for a specific Google user's account
try:
    GDrive(is_read_only=True, is_corporate_account=False)
    GDrive(is_read_only=False, is_corporate_account=False)
    NO_GDRIVE_PERSONAL = False
except:
    NO_GDRIVE_PERSONAL = True

skipif_no_gdrive_personal = pytest.mark.skipif(
    NO_GDRIVE_PERSONAL, reason='GDrive personal tokens not available'
)

try:
    GSheets(is_read_only=True, is_corporate_account=False)
    GSheets(is_read_only=False, is_corporate_account=False)
    NO_GSHEETS_PERSONAL = False
except:
    NO_GSHEETS_PERSONAL = True

skipif_no_gsheets_personal = pytest.mark.skipif(
    NO_GSHEETS_PERSONAL, reason='GSheets personal tokens not available'
)

IS_WINDOWS = sys.platform == 'win32'


@skipif_no_gdrive_personal
def test_gdrive_folder_id_exception_personal():
    drive = GDrive(is_corporate_account=False)

    # the folder does not exist
    folders = [
        'DoesNotExist',
        '/Google Drive/MSL/DoesNotExist',
    ]
    if IS_WINDOWS:
        folders.append(r'C:\Users\username\Google Drive\MSL\DoesNotExist')
    for folder in folders:
        with pytest.raises(OSError, match=r'Not a valid Google Drive folder'):
            drive.folder_id(folder)

    # specified a valid file (which is not a folder)
    files = {
        'Single-Photon Generation and Detection.pdf': '11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS',
        'MSL/msl-io-testing/unique': '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395',
    }
    for file, id_ in files.items():
        assert drive.file_id(file) == id_
        with pytest.raises(OSError, match=r'Not a valid Google Drive folder'):
            drive.folder_id(file)


@skipif_no_gdrive_personal
def test_gdrive_folder_id_personal():
    drive = GDrive(is_corporate_account=False)

    assert drive.folder_id('') == 'root'
    assert drive.folder_id('Google Drive') == 'root'
    if IS_WINDOWS:
        assert drive.folder_id(r'C:\Users\username\Google Drive') == 'root'
        assert drive.folder_id(r'D:\Google Drive') == 'root'

    assert drive.folder_id('MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    assert drive.folder_id('MSL/msl-io-testing') == '1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C'
    assert drive.folder_id('MSL/msl-io-testing/f 1/f2') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert drive.folder_id('/Google Drive/MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    assert drive.folder_id('Google Drive/MSL/msl-io-testing/f 1') == '1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9'
    if IS_WINDOWS:
        assert drive.folder_id(r'C:\Users\username\Google Drive\MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
        assert drive.folder_id(r'MSL\msl-io-testing\f 1\f2\sub folder 3') == '1wLAPHCOphcOITR37b8UB88eFW_FzeNQB'


@skipif_no_gdrive_personal
def test_gdrive_file_id_exception_personal():
    drive = GDrive(is_corporate_account=False)

    # file does not exist
    files = [
        'DoesNotExist',
        '/home/username/Google Drive/DoesNotExist.txt',
    ]
    if IS_WINDOWS:
        files.append(r'C:\Users\username\Google Drive\DoesNotExist.txt')
    for file in files:
        with pytest.raises(OSError, match=r'Not a valid Google Drive file'):
            drive.file_id(file)

    # specified a valid folder (which is not a file)
    folders = {
        'MSL': '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi',
        '/Google Drive/MSL': '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi',
    }
    if IS_WINDOWS:
        folders[r'C:\Users\username\Google Drive\MSL'] = '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    for folder, id_ in folders.items():
        assert drive.folder_id(folder) == id_
        with pytest.raises(OSError, match=r'Not a valid Google Drive file'):
            drive.file_id(folder)


@skipif_no_gdrive_personal
def test_gdrive_file_id_personal():
    drive = GDrive(is_corporate_account=False)
    files = {
        'Single-Photon Generation and Detection.pdf': '11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS',
        'MSL/msl-io-testing/unique': '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395',
        '/Google Drive/Single-Photon Generation and Detection.pdf': '11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS',
    }
    if IS_WINDOWS:
        files[r'C:\Users\username\Google Drive\MSL\msl-io-testing\unique'] = '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
        files[r'MSL\msl-io-testing\f 1\f2\New Text Document.txt'] = '1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP'

    for file, id_ in files.items():
        assert drive.file_id(file) == id_


@skipif_no_gdrive_personal
def test_gdrive_file_id_multiple_personal():
    # multiple files with the same name in the same folder
    drive = GDrive(is_corporate_account=False)

    path = 'MSL/msl-io-testing/f 1/electronics.xlsx'

    with pytest.raises(OSError) as err:
        drive.file_id(path)
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in str(err.value)
    assert GSheets.MIME_TYPE in str(err.value)

    mime_types = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '1aCSP8HU7mAz2hss8dP7IpNz0xJDzWSe1',
        GSheets.MIME_TYPE: '1SdLw6tlh4EaPeDis0pPepzYRBb_mx_i8fOwgODwQKaE',
    }
    for mime, id_ in mime_types.items():
        assert drive.file_id(path , mime_type=mime) == id_


@skipif_no_gdrive_personal
def test_gdrive_create_delete_folder_personal():

    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.create_folder('TEST')

    drive = GDrive(is_read_only=False, is_corporate_account=False)

    # create
    folders = [
        'TEST TEST TEST',
        'TEST-TEST-1/TEST 2/a b c',
    ]
    for folder in folders:
        folder_id = drive.create_folder(folder)
        assert drive.folder_id(folder) == folder_id

    # delete
    folders = [
        'TEST TEST TEST',
        'TEST-TEST-1/TEST 2/a b c',
        'TEST-TEST-1/TEST 2',
        'TEST-TEST-1',
    ]
    for folder in folders:
        drive.delete(drive.folder_id(folder))
        with pytest.raises(OSError):
            drive.folder_id(folder)


@skipif_no_gdrive_personal
def test_gdrive_is_file_personal():
    drive = GDrive(is_corporate_account=False)
    assert not drive.is_file('doesnotexist.txt')
    assert not drive.is_file('does/not/exist.txt')
    assert not drive.is_file('MSL')
    assert drive.is_file('MSL/msl-io-testing/unique')
    assert drive.is_file('MSL/msl-io-testing/f 1/electronics.xlsx')
    assert drive.is_file('MSL/msl-io-testing/f 1/electronics.xlsx', mime_type=GSheets.MIME_TYPE)

    if IS_WINDOWS:
        assert not drive.is_file(r'C:\Users\username\Google Drive\MSL\msl-io-testing\f 1')
        assert drive.is_file(r'MSL\msl-io-testing\f 1\f2\New Text Document.txt')


@skipif_no_gdrive_personal
def test_gdrive_is_folder_personal():
    drive = GDrive(is_corporate_account=False)
    assert not drive.is_folder('doesnotexist')
    assert not drive.is_folder('MSL/msl-io-testing/unique')
    assert drive.is_folder('MSL')
    assert drive.is_folder('MSL/msl-io-testing/f 1/f2/sub folder 3')

    if IS_WINDOWS:
        assert not drive.is_folder(r'MSL\msl-io-testing\f 1\electronics.xlsx')
        assert drive.is_folder(r'MSL\msl-io-testing\f 1')


@skipif_no_gdrive_personal
def test_gdrive_upload_personal():
    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.upload(__file__)

    drive = GDrive(is_read_only=False, is_corporate_account=False)
    file_id = drive.upload(
        __file__,
        folder_id=drive.folder_id('MSL'),
        mime_type='text/x-python'
    )

    path = os.path.join('MSL', os.path.basename(__file__))
    assert drive.file_id(path, mime_type='text/x-python') == file_id
    assert drive.file_id(path) == file_id
    assert not drive.is_file(path, mime_type='application/x-python-code')

    drive.delete(file_id)
    assert not drive.is_file(path)


@skipif_no_gdrive_personal
def test_gdrive_download_personal():

    drive = GDrive(is_corporate_account=False)

    file_id = drive.file_id('MSL/msl-io-testing/file.txt')

    # cannot be a string IO object
    with pytest.raises(TypeError):
        drive.download(file_id, save_as=io.StringIO())
    if not IS_PYTHON2:  # in Python 2, str and bytes are the same
        with pytest.raises(TypeError):
            drive.download(file_id, save_as=open('junk.txt', mode='wt'))
        os.remove('junk.txt')  # clean up since it got created before the error was raised

    # a BytesIO object
    with io.BytesIO() as buffer:
        drive.download(file_id, save_as=buffer)
        buffer.seek(0)
        assert buffer.read() == b'in "msl-io-testing"'

    # a file in 'wb' mode
    temp_file = os.path.join(tempfile.gettempdir(), 'msl-io-gdrive-download.txt')
    with open(temp_file, mode='wb') as fp:
        drive.download(file_id, save_as=fp)
    with open(temp_file) as fp:
        assert fp.read() == 'in "msl-io-testing"'
    os.remove(temp_file)  # clean up

    # do not specify a value for the 'save_as' kwarg
    # therefore the filename is determined from the remote filename
    file_id = drive.file_id('MSL/msl-io-testing/f 1/f2/sub folder 3/file.txt')
    drive.download(file_id)
    with open('file.txt', mode='r') as fp:
        assert fp.read() == 'in "sub folder 3"'
    os.remove('file.txt')  # clean up

    # save to a file with a different filename
    drive.download(file_id, save_as=temp_file)
    with open(temp_file, mode='rb') as fp:
        assert fp.read() == b'in "sub folder 3"'
    os.remove(temp_file)  # clean up

    # use a callback
    def handler(file):
        assert file.progress() == 1.0
        assert file.total_size == 17
        assert file.resumable_progress == 17
    drive.download(file_id, callback=handler)
    os.remove('file.txt')  # clean up


@skipif_no_gdrive_personal
def test_gdrive_empty_trash_personal():
    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.empty_trash()

    drive = GDrive(is_read_only=False, is_corporate_account=False)
    drive.empty_trash()


@skipif_no_gsheets_personal
def test_gsheets_sheet_names_personal():
    sheets = GSheets(is_corporate_account=False)

    # MSL/msl-io-testing/empty-5
    names = sheets.sheet_names('1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY')
    assert len(names) == 5
    assert 'Sheet1' in names
    assert 'Sheet2' in names
    assert 'Sheet3' in names
    assert 'Sheet4' in names
    assert 'Sheet5' in names

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment
    names = sheets.sheet_names('1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4')
    assert len(names) == 1
    assert 'Sensor_1' in names


@skipif_no_gsheets_personal
def test_gsheets_values_personal():
    sheets = GSheets(is_corporate_account=False)

    # MSL/msl-io-testing/empty-5
    empty_id = '1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY'

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment
    lab_id = '1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4'

    # more than 1 sheet exists
    with pytest.raises(ValueError, match=r'You must specify a sheet name:'):
        sheets.values(empty_id)

    # empty sheets are okay
    for name in sheets.sheet_names(empty_id):
        values = sheets.values(empty_id, sheet=name)
        assert isinstance(values, list)
        assert not values

        # specifying the cells in an empty sheet is okay
        values = sheets.values(empty_id, sheet=name, cells='A2:Z10')
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
    values = sheets.values(lab_id)
    assert values == expected

    values = sheets.values(lab_id, row_major=False)
    assert values == [[expected[r][c] for r in range(len(expected))] for c in range(len(expected[0]))]

    values = sheets.values(lab_id, cells='B2:C4')
    assert values == [[expected[r][c] for c in range(1, 3)] for r in range(1, 4)]


@skipif_no_gsheets_personal
def test_gsheets_to_datetime():
    sheets = GSheets(is_corporate_account=False)

    expected = [
        ['Timestamp', datetime(2021, 4, 3, 12, 36, 10), datetime(2021, 4, 3, 12, 37, 10),
         datetime(2021, 4, 3, 12, 38, 10), datetime(2021, 4, 3, 12, 39, 10)],
        ['Temperature', 20.33, 20.23, 20.41, 20.29],
        ['Humidity', 49.82, 46.06, 47.06, 48.32]
    ]

    # MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment
    lab_id = '1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4'
    values = sheets.values(lab_id, value_option='UNFORMATTED_VALUE', row_major=False)
    values[0][1:] = [sheets.to_datetime(t) for t in values[0][1:]]
    assert values == expected

    values = sheets.values(lab_id, value_option='UNFORMATTED_VALUE',
                           datetime_option='FORMATTED_STRING', row_major=False)
    expected[0][1:] = [str(t) for t in expected[0][1:]]
    assert values == expected