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
from msl.io import (
    GDrive,
    GSheets,
    GCell,
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
    files = [
        'Single-Photon Generation and Detection.pdf',
        'MSL/msl-io-testing/unique'
    ]
    for file in files:
        with pytest.raises(OSError, match=r'Not a valid Google Drive folder'):
            drive.folder_id(file)

    # specify an invalid parent ID
    assert drive.folder_id('MSL') == '14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi'
    with pytest.raises(HttpError):
        drive.folder_id('MSL', parent_id='INVALID_Kmkjo9aCQGysOsxwkTtpoJODi')


@skipif_no_gdrive_personal
def test_gdrive_folder_id_personal():
    drive = GDrive(is_corporate_account=False)

    # relative to the root folder
    assert drive.folder_id('') == 'root'
    assert drive.folder_id('/') == 'root'
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

    # relative to a parent folder
    assert drive.folder_id('msl-io-testing', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C'
    assert drive.folder_id('msl-io-testing/f 1/f2', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert drive.folder_id('f 1/f2', parent_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert drive.folder_id('f2', parent_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9') == '1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN'
    assert drive.folder_id('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN') == '1wLAPHCOphcOITR37b8UB88eFW_FzeNQB'


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
    folders = [
        'MSL',
        '/Google Drive/MSL',
    ]
    if IS_WINDOWS:
        folders.append(r'C:\Users\username\Google Drive\MSL')
    for folder in folders:
        with pytest.raises(OSError, match=r'Not a valid Google Drive file'):
            drive.file_id(folder)

    # specify an invalid parent ID
    assert drive.file_id('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    with pytest.raises(HttpError):
        drive.file_id('unique', folder_id='INVALID_NCuTWxmABs-w7JenftaLGAG9C')


@skipif_no_gdrive_personal
def test_gdrive_file_id_personal():
    drive = GDrive(is_corporate_account=False)

    # relative to the root folder
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

    # relative to a parent folder
    assert drive.file_id('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    assert drive.file_id('msl-io-testing/unique', folder_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == '1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395'
    assert drive.file_id('file.txt', folder_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB') == '1CDS3cWDItXB1uLCPGq0uy6OJAngkmNoD'
    assert drive.file_id('f 1/f2/New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == '1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP'


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
        assert drive.file_id(path, mime_type=mime) == id_


@skipif_no_gdrive_personal
def test_gdrive_create_delete_folder_personal():

    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.create_folder('TEST')

    drive = GDrive(is_read_only=False, is_corporate_account=False)

    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())

    # create (relative to root)
    for folder in [u1, u2 + '/sub-2/a b c']:
        folder_id = drive.create_folder(folder)
        assert drive.folder_id(folder) == folder_id

    # delete
    for folder in [u1, u2 + '/sub-2/a b c', u2 + '/sub-2', u2]:
        drive.delete(drive.folder_id(folder))
        with pytest.raises(OSError, match='Not a valid Google Drive folder'):
            drive.folder_id(folder)

    # create (relative to a parent folder)
    # ID of "MSL/msl-io-testing/f 1/f2/sub folder 3" is "1wLAPHCOphcOITR37b8UB88eFW_FzeNQB"
    u3 = str(uuid.uuid4())
    folder_id = drive.create_folder(u3 + '/a/b/c', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert drive.folder_id('MSL/msl-io-testing/f 1/f2/sub folder 3/' + u3 + '/a/b/c') == folder_id

    # these should not raise an error (do not need to assert anything)
    u3_id = drive.folder_id(u3, parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    u3_a_id = drive.folder_id('a', parent_id=u3_id)
    u3_a_b_id = drive.folder_id('b', parent_id=u3_a_id)
    u3_a_b_c_id = drive.folder_id('c', parent_id=u3_a_b_id)

    # deleting a folder should also delete the children folders
    drive.delete(u3_id)
    assert drive.is_folder('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert not drive.is_folder(u3 + '/a/b/c', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not drive.is_folder(u3 + '/a/b', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not drive.is_folder(u3 + '/a', parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')
    assert not drive.is_folder(u3, parent_id='1wLAPHCOphcOITR37b8UB88eFW_FzeNQB')


@skipif_no_gdrive_personal
def test_gdrive_is_file_personal():
    drive = GDrive(is_corporate_account=False)

    # relative to the root folder
    assert not drive.is_file('doesnotexist.txt')
    assert not drive.is_file('does/not/exist.txt')
    assert not drive.is_file('MSL')
    assert drive.is_file('MSL/msl-io-testing/unique')
    assert drive.is_file('MSL/msl-io-testing/f 1/electronics.xlsx')
    assert drive.is_file('MSL/msl-io-testing/f 1/electronics.xlsx', mime_type=GSheets.MIME_TYPE)
    if IS_WINDOWS:
        assert not drive.is_file(r'C:\Users\username\Google Drive\MSL\msl-io-testing\f 1')
        assert drive.is_file(r'MSL\msl-io-testing\f 1\f2\New Text Document.txt')

    # relative to a parent folder
    assert drive.is_file('unique', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')
    assert drive.is_file('msl-io-testing/unique', folder_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi')
    assert drive.is_file('Single-Photon Generation and Detection.pdf', folder_id='root')
    assert drive.is_file('f 1/f2/New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')
    assert not drive.is_file('f2', folder_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9')
    assert not drive.is_file('New Text Document.txt', folder_id='1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C')

    # relative to an invalid parent folder
    with pytest.raises(HttpError):
        drive.is_file('unique', folder_id='INVALID_NCuTWxmABs-w7JenftaLGAG9C')


@skipif_no_gdrive_personal
def test_gdrive_is_folder_personal():
    drive = GDrive(is_corporate_account=False)

    # relative to the root folder
    assert not drive.is_folder('doesnotexist')
    assert not drive.is_folder('MSL/msl-io-testing/unique')
    assert drive.is_folder('MSL')
    assert drive.is_folder('MSL/msl-io-testing/f 1/f2/sub folder 3')
    if IS_WINDOWS:
        assert not drive.is_folder(r'MSL\msl-io-testing\f 1\electronics.xlsx')
        assert drive.is_folder(r'MSL\msl-io-testing\f 1')

    # relative to a parent folder
    assert not drive.is_folder('doesnotexist', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert not drive.is_folder('sub folder 3xx', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert drive.is_folder('sub folder 3', parent_id='1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN')
    assert drive.is_folder('f2', parent_id='1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9')
    assert drive.is_folder('msl-io-testing/f 1/f2', parent_id='14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi')

    # relative to an invalid parent folder
    with pytest.raises(HttpError):
        drive.is_folder('f2', parent_id='INVALID_F5AhbUb7Lq77qzuBbvZr150X9')


@skipif_no_gdrive_personal
def test_gdrive_upload_personal():
    temp_file = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + '.py')
    with open(temp_file, mode='w') as fp:
        fp.write('from msl.io import GDrive')

    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.upload(temp_file)

    drive = GDrive(is_read_only=False, is_corporate_account=False)
    file_id = drive.upload(
        temp_file,
        folder_id=drive.folder_id('MSL'),
        mime_type='text/x-python'
    )

    path = os.path.join('MSL', os.path.basename(temp_file))
    assert drive.file_id(path, mime_type='text/x-python') == file_id
    assert drive.file_id(path) == file_id
    assert not drive.is_file(path, mime_type='application/x-python-code')

    drive.delete(file_id)
    assert not drive.is_file(path)
    os.remove(temp_file)


@skipif_no_gdrive_personal
def test_gdrive_download_personal():
    temp_file = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))

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

    # a file handle in 'wb' mode
    with open(temp_file, mode='wb') as fp:
        drive.download(file_id, save_as=fp)
    with open(temp_file, mode='rt') as fp:
        assert fp.read() == 'in "msl-io-testing"'
    os.remove(temp_file)  # clean up

    # do not specify a value for the 'save_as' kwarg
    # therefore the filename is determined from the remote filename
    # and saved to the current working directory
    file_id = drive.file_id('MSL/msl-io-testing/f 1/f2/sub folder 3/file.txt')
    drive.download(file_id)
    with open('file.txt', mode='r') as fp:
        assert fp.read() == 'in "sub folder 3"'
    os.remove('file.txt')  # clean up

    # save to a specific file
    assert not os.path.isfile(temp_file)
    drive.download(file_id, save_as=temp_file)
    with open(temp_file, mode='rb') as fp:
        assert fp.read() == b'in "sub folder 3"'
    os.remove(temp_file)  # clean up

    # use a callback
    def handler(file):
        assert file.progress() == 1.0
        assert file.total_size == 17
        assert file.resumable_progress == 17
    drive.download(file_id, save_as=temp_file, callback=handler)
    os.remove(temp_file)  # clean up


@skipif_no_gdrive_personal
def test_gdrive_empty_trash_personal():
    # instantiate in read-only mode
    drive = GDrive(is_read_only=True, is_corporate_account=False)
    with pytest.raises(HttpError, match='Insufficient Permission'):
        drive.empty_trash()

    drive = GDrive(is_read_only=False, is_corporate_account=False)
    drive.empty_trash()


@skipif_no_gdrive_personal
def test_gdrive_path_personal():
    drive = GDrive(is_corporate_account=False)
    assert drive.path('0AFP6574OTgaaUk9PVA') == 'My Drive'
    assert drive.path('11yaxZH93B0IhQZwfCeo2dXb-Iduh-4dS') == 'My Drive/Single-Photon Generation and Detection.pdf'
    assert drive.path('14GYO5FIKmkjo9aCQGysOsxwkTtpoJODi') == 'My Drive/MSL'
    assert drive.path('1oB5i-YcNCuTWxmABs-w7JenftaLGAG9C') == 'My Drive/MSL/msl-io-testing'
    assert drive.path('1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY') == 'My Drive/MSL/msl-io-testing/empty-5'
    assert drive.path('1HG_emhGXBGaR7oS6ftioJOF-xbl1kv41') == 'My Drive/MSL/msl-io-testing/file.txt'
    assert drive.path('1iaLNB_IZNxbFlpy-Z2-22WQGWy4wU395') == 'My Drive/MSL/msl-io-testing/unique'
    assert drive.path('1mhQ_9iVF5AhbUb7Lq77qzuBbvZr150X9') == 'My Drive/MSL/msl-io-testing/f 1'
    assert drive.path('1SdLw6tlh4EaPeDis0pPepzYRBb_mx_i8fOwgODwQKaE') == 'My Drive/MSL/msl-io-testing/f 1/electronics.xlsx'
    assert drive.path('1aCSP8HU7mAz2hss8dP7IpNz0xJDzWSe1') == 'My Drive/MSL/msl-io-testing/f 1/electronics.xlsx'
    assert drive.path('1NRD4klmRTQDkh5ZfhnhaHc6hDYfklMJN') == 'My Drive/MSL/msl-io-testing/f 1/f2'
    assert drive.path('1qW1QclelxZtJtKMigCgGH4ST3QoJ9zuP') == 'My Drive/MSL/msl-io-testing/f 1/f2/New Text Document.txt'
    assert drive.path('1wLAPHCOphcOITR37b8UB88eFW_FzeNQB') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3'
    assert drive.path('1CDS3cWDItXB1uLCPGq0uy6OJAngkmNoD') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3/file.txt'
    assert drive.path('1FwzsFgN7w-HZXOlUAEMVMSOGpNHCj5NXvH6Xl7LyLp4') == 'My Drive/MSL/msl-io-testing/f 1/f2/sub folder 3/lab environment'


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


@skipif_no_gsheets_personal
def test_gsheets_cells():
    sheets = GSheets(is_corporate_account=False)

    # MSL/msl-io-testing/empty-5
    empty_id = '1Ua15pRGUH5qoU0c3Ipqrkzi9HBlm3nzqCn5O1IONfCY'

    # data-types
    datatypes_id = '1zMO4wk0IPC9I57dR5WoPTzlOX6g5-AcnwGFOEHrhIHU'

    # valid spreadsheet_id, invalid sheet name
    with pytest.raises(ValueError, match=r'No sheet exists'):
        sheets.cells(datatypes_id, sheet='invalid')

    # valid spreadsheet_id, multiple sheets
    with pytest.raises(ValueError, match=r'You must specify a sheet name:'):
        sheets.cells(empty_id)

    assert sheets.cells(empty_id, sheet='Sheet1') == []

    cells = sheets.cells(datatypes_id)

    assert len(cells) == 18

    assert len(cells[0]) == 6
    assert cells[0][0] == GCell(value='Automatic', type='STRING', formatted='Automatic')
    assert cells[0][1] == GCell(value=1.23, type='NUMBER', formatted='1.23')
    assert cells[0][2] == GCell(value='string', type='STRING', formatted='string')
    assert cells[0][3] == GCell(value=1, type='NUMBER', formatted='1')
    assert cells[0][4] == GCell(value='0123456789', type='STRING', formatted='0123456789')
    assert cells[0][5] == GCell(value=36982, type='DATE', formatted='1 April 2001')

    assert len(cells[1]) == 3
    assert cells[1][0] == GCell(value='Plain text', type='STRING', formatted='Plain text')
    assert cells[1][1] == GCell(value='a b c d', type='STRING', formatted='a b c d')
    assert cells[1][2] == GCell(value='34', type='STRING', formatted='34')

    assert len(cells[2]) == 2
    assert cells[2][0] == GCell(value='Number', type='STRING', formatted='Number')
    assert cells[2][1] == GCell(value=1234.56789, type='NUMBER', formatted='1,234.57')

    assert len(cells[3]) == 2
    assert cells[3][0] == GCell(value='Percent', type='STRING', formatted='Percent')
    assert cells[3][1] == GCell(value=0.542, type='PERCENT', formatted='54.20%')

    assert len(cells[4]) == 2
    assert cells[4][0] == GCell(value='Scientific', type='STRING', formatted='Scientific')
    assert cells[4][1] == GCell(value=0.00321, type='SCIENTIFIC', formatted='3.21E-03')

    assert len(cells[5]) == 3
    assert cells[5][0] == GCell(value='Accounting', type='STRING', formatted='Accounting')
    assert cells[5][1] == GCell(value=99.95, type='NUMBER', formatted=' $ 99.95 ')
    assert cells[5][2] == GCell(value=-23.45, type='NUMBER', formatted=' $ (23.45)')

    assert len(cells[6]) == 3
    assert cells[6][0] == GCell(value='Financial', type='STRING', formatted='Financial')
    assert cells[6][1] == GCell(value=1.23, type='NUMBER', formatted='1.23')
    assert cells[6][2] == GCell(value=-1.23, type='NUMBER', formatted='(1.23)')

    assert len(cells[7]) == 3
    assert cells[7][0] == GCell(value='Currency', type='STRING', formatted='Currency')
    assert cells[7][1] == GCell(value=99.95, type='CURRENCY', formatted='$99.95')
    assert cells[7][2] == GCell(value=-1.99, type='CURRENCY', formatted='-$1.99')

    assert len(cells[8]) == 3
    assert cells[8][0] == GCell(value='Currency (rounded)', type='STRING', formatted='Currency (rounded)')
    assert cells[8][1] == GCell(value=99.95, type='CURRENCY', formatted='$100')
    assert cells[8][2] == GCell(value=-1.99, type='CURRENCY', formatted='-$2')

    assert len(cells[9]) == 2
    assert cells[9][0] == GCell(value='Date', type='STRING', formatted='Date')
    assert cells[9][1] == GCell(value=17738, type='DATE', formatted='24/07/1948')

    assert len(cells[10]) == 3
    assert cells[10][0] == GCell(value='Time', type='STRING', formatted='Time')
    assert cells[10][1] == GCell(value=0.2661689814814815, type='TIME', formatted='06:23:17')
    assert cells[10][2] == GCell(value=0.7378356481481482, type='TIME', formatted='17:42:29')

    assert len(cells[11]) == 2
    assert cells[11][0] == GCell(value='Date time', type='STRING', formatted='Date time')
    assert cells[11][1] == GCell(value=34736.4303472222222222, type='DATE_TIME', formatted='06/02/1995 10:19:42')

    assert len(cells[12]) == 2
    assert cells[12][0] == GCell(value='Duration', type='STRING', formatted='Duration')
    assert cells[12][1] == GCell(value=1.000023148148148, type='TIME', formatted='24:00:02')

    assert len(cells[13]) == 2
    assert cells[13][0] == GCell(value='Formula', type='STRING', formatted='Formula')
    assert cells[13][1] == GCell(value=6.747908247937978, type='SCIENTIFIC', formatted='6.75E+00')

    assert len(cells[14]) == 3
    assert cells[14][0] == GCell(value='Error', type='STRING', formatted='Error')
    assert cells[14][1] == GCell(value='#DIV/0! (Function DIVIDE parameter 2 cannot be zero.)', type='ERROR',
                                 formatted='#DIV/0!')
    assert cells[14][2] == GCell(
        value="#VALUE! (Function MULTIPLY parameter 2 expects number values. "
              "But 'Currency' is a text and cannot be coerced to a number.)",
        type='ERROR', formatted='#VALUE!')

    assert len(cells[15]) == 3
    assert cells[15][0] == GCell(value='Empty', type='STRING', formatted='Empty')
    assert cells[15][1] == GCell(value=None, type='EMPTY', formatted='')
    assert cells[15][2] == GCell(value='<== keep B16 empty', type='STRING', formatted='<== keep B16 empty')

    assert len(cells[16]) == 3
    assert cells[16][0] == GCell(value='Boolean', type='STRING', formatted='Boolean')
    assert cells[16][1] == GCell(value=True, type='BOOLEAN', formatted='TRUE')
    assert cells[16][2] == GCell(value=False, type='BOOLEAN', formatted='FALSE')

    assert len(cells[17]) == 2
    assert cells[17][0] == GCell(value='Custom', type='STRING', formatted='Custom')
    assert cells[17][1] == GCell(value=12345.6789, type='NUMBER', formatted='12345 55/81')
