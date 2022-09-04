import os
import re
import sys
import stat
import uuid
import shutil
import hashlib
import datetime
import tempfile
import subprocess
from io import BytesIO, StringIO
try:
    PermissionError
except NameError:
    PermissionError = OSError  # for Python 2.7

import pytest

from msl.io import utils


def test_search():

    def s(**kwargs):
        return list(utils.search(base, **kwargs))

    # the msl-io folder
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    assert base.endswith('msl-io')

    # (?!c) means match __init__.py files but ignore __init__.pyc files
    files = s(pattern=r'__init__\.py(?!c)')
    assert len(files) == 0

    files = s(pattern=r'__init__\.py(?!c)', levels=1)
    assert len(files) == 1

    files = s(pattern=r'__init__\.py(?!c)', levels=2)
    assert len(files) == 3

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders=r'v?env')
    assert len(files) == 6

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders=['readers', 'v?env'])
    assert len(files) == 5

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders=['readers', 'writers', 'v?env'])
    assert len(files) == 4

    files = s(pattern=r'authors')
    assert len(files) == 0

    files = s(pattern=r'authors', regex_flags=re.IGNORECASE)
    assert len(files) == 1

    files = s(pattern=r'setup')
    assert len(files) == 2

    files = s(pattern=r'README', levels=None, exclude_folders='v?env')
    assert len(files) == 1

    files = s(pattern=r'README', levels=None, ignore_hidden_folders=False,
              exclude_folders=['.eggs', '.pytest_cache', '.cache', 'v?env'])
    assert len(files) == 1

    files = s(pattern=r'(^in|^auth)', levels=1, exclude_folders='htmlcov')
    assert len(files) == 3

    files = s(pattern=r'(^in|^auth)', levels=1, regex_flags=re.IGNORECASE, exclude_folders='htmlcov')
    assert len(files) == 4


def test_git_head():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    head = utils.git_head(root_dir)
    assert len(head['hash']) == 40
    assert all(char.isalnum() for char in head['hash'])
    if sys.version_info.major > 2:
        assert isinstance(head['hash'], str)
    assert isinstance(head['datetime'], datetime.datetime)

    # can specify any directory within the version control hierarchy
    assert utils.git_head(os.path.join(root_dir, '.git')) == head
    assert utils.git_head(os.path.join(root_dir, 'msl', 'examples', 'io')) == head
    assert utils.git_head(os.path.dirname(__file__)) == head
    assert utils.git_head(os.path.join(root_dir, 'docs', '_api')) == head

    # a directory not under version control
    assert utils.git_head(tempfile.gettempdir()) is None


def test_checksum():
    path = os.path.join(os.path.dirname(__file__), 'samples', 'hdf5_sample.h5')
    sha256 = 'e5dad4f15335e603fd602c22bf9ddb71b3500f862905495d3d17e6159a463d2d'
    md5 = 'a46708df266595218db2ba06788c4695'

    # use a filename as a string
    assert isinstance(path, str)
    assert sha256 == utils.checksum(path, algorithm='sha256')
    assert md5 == utils.checksum(path, algorithm='md5')

    # use a filename as bytes
    path_as_bytes = path.encode()
    assert isinstance(path_as_bytes, bytes)
    assert sha256 == utils.checksum(path_as_bytes, algorithm='sha256')
    assert md5 == utils.checksum(path_as_bytes, algorithm='md5')

    # use a file pointer (binary mode)
    with open(path, mode='rb') as fp:
        assert sha256 == utils.checksum(fp, algorithm='sha256')
    with open(path, mode='rb') as fp:
        assert md5 == utils.checksum(fp, algorithm='md5')

    # use a byte buffer
    with open(path, mode='rb') as fp:
        buffer = BytesIO(fp.read())
    assert buffer.tell() == 0
    assert sha256 == utils.checksum(buffer, algorithm='sha256')
    assert buffer.tell() == 0
    assert md5 == utils.checksum(buffer, algorithm='md5')
    assert buffer.tell() == 0

    # ensure that all available algorithms can be used
    for algorithm in hashlib.algorithms_available:
        value = utils.checksum(path, algorithm=algorithm)
        assert isinstance(value, str)

    # file does not exist
    with pytest.raises((IOError, OSError), match='does_not_exist.txt'):
        utils.checksum('/the/file/does_not_exist.txt')
    with pytest.raises((IOError, OSError), match='does_not_exist.txt'):
        utils.checksum(b'/the/file/does_not_exist.txt')

    # invalid type
    with pytest.raises(TypeError):
        utils.checksum(None)
    with pytest.raises(TypeError):
        utils.checksum(bytearray(buffer.getvalue()))
    with pytest.raises(TypeError):
        utils.checksum(memoryview(buffer.getvalue()))

    # unsupported algorithm
    with pytest.raises(ValueError, match=r'unsupported'):
        utils.checksum(path, algorithm='invalid')


def test_get_basename():
    paths = [
        '/a/b/c/d/e/file.dat',
        'file.dat',
        '/a/file.dat',
        u'/something/file.dat',
        'file://a.b.c.d/folder/file.dat',
    ]
    if sys.platform == 'win32':
        paths.extend([
            'C:\\a\\b\\c\\d\\e\\file.dat',
            r'C:\a\file.dat',
            u'D:/file.dat',
            r'\\a.b.c.d\folder\file.dat',
            '\\\\a.b.c.d\\folder\\file.dat',
        ])
    for path in paths:
        assert utils.get_basename(path) == 'file.dat'
        assert utils.get_basename(path.encode()) == b'file.dat'

    assert utils.get_basename(StringIO(u'hello')) == u'StringIO'
    assert utils.get_basename(BytesIO(b'hello')) == 'BytesIO'

    with open(__file__, mode='rt') as fp:
        assert utils.get_basename(fp) == 'test_utils.py'


def test_copy():

    def check_stat(dest):
        src_stat = os.stat(__file__)
        dst_stat = os.stat(dest)
        for attr in dir(src_stat):
            if not attr.startswith('st_'):
                continue
            if attr in ['st_ino', 'st_ctime', 'st_ctime_ns', 'st_birthtime']:  # these will never be equal
                continue
            src_value = getattr(src_stat, attr)
            dst_value = getattr(dst_stat, attr)
            if attr == 'st_file_attributes':
                # on Windows the FILE_ATTRIBUTE_NOT_CONTENT_INDEXED attribute may not be copied
                if (src_value != dst_value) and (src_value + 0x2000 != dst_value):
                    return False
            elif 'time' in attr:  # times can be approximate
                if attr.endswith('ns'):
                    if abs(src_value - dst_value) > 1e4:
                        return False
                elif abs(src_value - dst_value) > 1e-4:
                    return False
            elif attr == 'st_dev' and sys.platform == 'win32' and os.getenv('GITHUB_ACTIONS'):
                # the ST_DEV values are not equal if the tests are run
                # via GitHub Actions and the OS is Windows
                pass
            elif src_value != dst_value:
                return False
        return True

    # make sure there is no remnant file from a previously-failed test
    if os.path.isfile(os.path.join(tempfile.gettempdir(), 'test_utils.py')):
        os.remove(os.path.join(tempfile.gettempdir(), 'test_utils.py'))

    # source file does not exist
    for item in [r'/the/file/does_not_exist.txt', r'/the/file/does_not_exist', r'does_not_exist']:
        with pytest.raises((IOError, OSError), match=item):
            utils.copy(item, '')

    # destination invalid
    with pytest.raises((IOError, OSError), match=r"''"):
        utils.copy(__file__, '')

    # copy (with metadata) to a directory that already exists
    dst = utils.copy(__file__, tempfile.gettempdir())
    assert dst == os.path.join(tempfile.gettempdir(), 'test_utils.py')
    assert check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)

    # destination already exists
    with pytest.raises(OSError, match=r'Will not overwrite'):
        utils.copy(__file__, dst)
    with pytest.raises(OSError, match=r'Will not overwrite'):
        utils.copy(__file__, tempfile.gettempdir())

    # can overwrite (with metadata), specify full path
    dst2 = utils.copy(__file__, dst, overwrite=True)
    assert dst2 == dst
    assert check_stat(dst2)
    assert utils.checksum(__file__) == utils.checksum(dst2)

    # can overwrite (without metadata), specify full path
    dst3 = utils.copy(__file__, dst, overwrite=True, include_metadata=False)
    assert dst3 == dst
    assert not check_stat(dst3)
    assert utils.checksum(__file__) == utils.checksum(dst3)

    # can overwrite (with metadata), specify directory only
    dst4 = utils.copy(__file__, tempfile.gettempdir(), overwrite=True)
    assert dst4 == dst
    assert check_stat(dst4)
    assert utils.checksum(__file__) == utils.checksum(dst4)

    os.remove(dst)

    # copy without metadata
    dst = utils.copy(__file__, tempfile.gettempdir(), include_metadata=False)
    assert dst == os.path.join(tempfile.gettempdir(), 'test_utils.py')
    assert not check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    os.remove(dst)

    # copy (without metadata) but use a different destination basename
    destination = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + '.tmp')
    dst = utils.copy(__file__, destination, include_metadata=False)
    assert dst == destination
    assert not check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    os.remove(dst)

    # copy to a directory that does not exist
    new_dirs = str(uuid.uuid4()).split('-')
    assert not os.path.isdir(os.path.join(tempfile.gettempdir(), new_dirs[0]))
    destination = os.path.join(tempfile.gettempdir(), *new_dirs)
    destination = os.path.join(destination, 'new_file.tmp')
    dst = utils.copy(__file__, destination)
    assert dst == destination
    assert check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    shutil.rmtree(os.path.join(tempfile.gettempdir(), new_dirs[0]))


def test_remove_write_permissions():

    # create a new file
    path = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + '.tmp')
    with open(path, mode='wb') as fp:
        fp.write(b'hello')

    # set to rwxrwxrwx
    os.chmod(path, 0o777)

    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        assert mode == 0o666  # Windows does not have the Execute permission
    else:
        assert mode == 0o777

    # can still modify it
    with open(path, mode='ab') as fp:
        fp.write(b' world')
    with open(path, mode='rb') as fp:
        assert fp.read() == b'hello world'

    utils.remove_write_permissions(path)

    # the Read and Execute permissions are preserved
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        assert mode == 0o444  # Windows does not have the Execute permission
    else:
        assert mode == 0o555

    # cannot open the file to modify it
    for m in ['wb', 'ab', 'wt', 'at', 'w+', 'w+b']:
        with pytest.raises((IOError, OSError)):
            open(path, mode=m)

    # cannot delete the file (only valid on Windows)
    if sys.platform == 'win32':
        with pytest.raises(OSError):
            os.remove(path)

    # can still read it
    with open(path, mode='rb') as fp:
        assert fp.read() == b'hello world'

    # set to rw--wxrw-
    os.chmod(path, 0o636)
    # remove and check permissions
    utils.remove_write_permissions(path)
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        # Windows does not have the Execute permission
        # and if any of the Read permissions are enabled then it
        # is enabled for the User, Group and Others
        assert mode == 0o444
    else:
        assert mode == 0o414

    # clean up by deleting the file
    os.chmod(path, 0o777)
    os.remove(path)


def test_is_file_readable():
    assert utils.is_file_readable(__file__)

    for item in [None, '', __file__+'py', dict()]:
        assert not utils.is_file_readable(item)

    with pytest.raises(TypeError):
        utils.is_file_readable(None, strict=True)

    with pytest.raises((IOError, OSError)):
        utils.is_file_readable('', strict=True)

    with pytest.raises((IOError, OSError)):
        utils.is_file_readable(__file__+'py', strict=True)


def test_is_dir_accessible():
    assert utils.is_dir_accessible(os.path.dirname(__file__))

    for item in [None, '', __file__, dict()]:
        assert not utils.is_dir_accessible(item)

    with pytest.raises(TypeError):
        utils.is_dir_accessible(None, strict=True)

    with pytest.raises(OSError):
        utils.is_dir_accessible('', strict=True)

    with pytest.raises(OSError):
        utils.is_dir_accessible(__file__, strict=True)


def test_is_admin():
    assert isinstance(utils.is_admin(), bool)


@pytest.mark.skipif(utils.is_admin(), reason='don\'t run if already an admin')
@pytest.mark.skipif(os.name != 'nt', reason='non-Windows OS')
def test_run_as_admin():
    # Using verb=None as a keyword argument allows for testing the
    # 'run_as_admin' function without getting the UAC prompt,
    # but the test command must not require admin privileges.
    # Only test on a non-admin Windows session because the other cases:
    #   1) already an admin
    #   2) running on POSIX
    # are straightforward implementations and we don't want to test
    # the subprocess.check_output internals.

    with pytest.raises(ValueError, match=r'args and/or an executable$'):
        utils.run_as_admin()

    # Don't want Windows to return b'ECHO is on.\r\n'
    out = utils.run_as_admin(args='echo 1', verb=None)
    assert out == b'1 \r\n'
    out = utils.run_as_admin(args=['echo', '1'], verb=None)
    assert out == b'1 \r\n'

    # no extra space after "hi"
    out = utils.run_as_admin(args='echo hi', verb=None)
    assert out == b'hi\r\n'

    # pass in the keyword argument "args=" as a positional argument
    out = utils.run_as_admin('echo hi', verb=None)
    assert out == b'hi\r\n'

    # run a batch file with spaces in the file path and in the arguments
    file = os.path.join(tempfile.gettempdir(), 'msl io batch script.bat')
    with open(file, mode='wt') as fp:
        fp.write('@ECHO OFF\r\n')
        for i in range(1, 6):
            fp.write('echo %{}\r\n'.format(i))

    expected = b'ECHO is off.\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\n'
    out = utils.run_as_admin(args='"{}"'.format(file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file], verb=None)
    assert out == expected
    out = utils.run_as_admin(executable=file, verb=None)
    assert out == expected

    expected = b'pi\r\n-p\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\n'
    out = utils.run_as_admin(args='"{}" pi -p'.format(file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, 'pi', '-p'], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=['pi', '-p'], executable=file, verb=None)
    assert out == expected

    expected = b'pi\r\n-p\r\n"hel lo"\r\nECHO is off.\r\nECHO is off.\r\n'
    out = utils.run_as_admin(args='"{}" pi -p "hel lo"'.format(file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, 'pi', '-p', 'hel lo'], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=['pi', '-p', 'hel lo'], executable=file, verb=None)
    assert out == expected

    expected = b'pi\r\n-p\r\n"hel lo"\r\n6\r\n"last parameter received"\r\n'
    out = utils.run_as_admin(args='"{}" pi -p "hel lo" 6 "last parameter received"'.format(file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, 'pi', '-p', 'hel lo', '6', 'last parameter received'], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=['pi', '-p', 'hel lo', '6', 'last parameter received'], executable=file, verb=None)
    assert out == expected

    # change directory
    out = utils.run_as_admin(
        args=[os.path.basename(file), 'pi', '-p', 'hel lo', '6', 'last parameter received'],
        cwd=os.path.dirname(file),
        verb=None
    )
    assert out == expected

    os.remove(file)

    # call the Python interpreter
    expected = subprocess.check_output([sys.executable, '-VV'])
    out = utils.run_as_admin(args='-VV', executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args='{} -VV'.format(sys.executable), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, '-VV'], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=['-VV'], executable=sys.executable, verb=None)
    assert out == expected

    # run a python script
    file = os.path.join(tempfile.gettempdir(), 'msl_io_admin_test.py')
    with open(file, mode='wt') as fp:
        fp.write('from __future__ import print_function\r\n')
        fp.write('import sys\r\n')
        # additional packages must be available since msl-io depends on them
        fp.write('import numpy\r\n')
        fp.write('import xlrd\r\n')
        fp.write('print(sys.executable)\r\n')
        fp.write('print(sys.argv[1:])\r\n')
        fp.write('print("written to stderr", file=sys.stderr)\r\n')

    # no arguments
    expected = '{}\r\n[]\r\n'.format(sys.executable).encode()
    out = utils.run_as_admin(args=file, executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args='{} {}'.format(sys.executable, file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file], executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, file], verb=None)
    assert out == expected

    # with arguments
    expected = "{}\r\n['1', 'x=5', 'a b c d', 'e']\r\n".format(sys.executable).encode()
    out = utils.run_as_admin(args='{} 1 x=5 "a b c d" e'.format(file), executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args='{} {} 1 x=5 "a b c d" e'.format(sys.executable, file), verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, '1', 'x=5', 'a b c d', 'e'], executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, file, '1', 'x=5', 'a b c d', 'e'], verb=None)
    assert out == expected

    # change directory
    expected = "{}\r\n['1']\r\n".format(sys.executable).encode()
    out = utils.run_as_admin(args=[sys.executable, os.path.basename(file), '1'], cwd=os.path.dirname(file), verb=None)
    assert out == expected

    # capture_stderr=True
    out = utils.run_as_admin(args=[sys.executable, file], capture_stderr=True, verb=None)
    assert b'written to stderr' in out

    os.remove(file)

    # raise some exceptions
    with pytest.raises(PermissionError):
        utils.run_as_admin('sc create MSL-IO-TEST binPath= "C:\\hello world\\dummy.exe"', verb=None)

    with pytest.raises(PermissionError):
        utils.run_as_admin(['sc', 'create', 'MSL-IO-TEST', 'binPath=', 'C:\\hello world\\dummy.exe'], verb=None)

    with pytest.raises(OSError, match=r'Set capture_stderr=True to see if more information is available.$'):
        utils.run_as_admin('doesnotexist.exe', verb=None)

    with pytest.raises(OSError, match=r"'doesnotexist.exe' is not recognized as an internal or external command"):
        utils.run_as_admin('doesnotexist.exe', capture_stderr=True, verb=None)

    with pytest.raises(OSError, match=r'Set show=False to capture the stdout stream.$'):
        utils.run_as_admin([sys.executable, '-c', '1/0'], show=True, verb=None)

    with pytest.raises(OSError, match=r'Set capture_stderr=True to see if more information is available.$'):
        utils.run_as_admin([sys.executable, '-c', '1/0'], verb=None)

    with pytest.raises(OSError, match=r'Set capture_stderr=True to see if more information is available.\nHello!$'):
        utils.run_as_admin([sys.executable, '-c', 'print("Hello!");1/0'], verb=None)

    with pytest.raises(OSError, match=r'ZeroDivisionError:'):
        utils.run_as_admin([sys.executable, '-c', '1/0'], capture_stderr=True, verb=None)


def test_prepare_email():
    temp = os.path.join(tempfile.gettempdir(), '793a7e5d-7e0e-4049-9e9b-f4383b7bb96a.tmp')

    def create(lines):
        with open(temp, mode='wt') as fp:
            fp.write('\n'.join(lines))

    with pytest.raises(OSError):
        utils._prepare_email('does-not-exist.ini', '', '')

    create(['[smtp]', '[gmail]'])
    with pytest.raises(ValueError, match='Cannot specify both'):
        utils._prepare_email(temp, '', None)

    create(['[unknown]'])
    with pytest.raises(ValueError, match='Must create either'):
        utils._prepare_email(temp, '', None)

    for item in (['[smtp]'], ['[smtp]', 'host=hostname'], ['[smtp]', 'port=25']):
        create(item)
        with pytest.raises(ValueError, match="Must specify the 'host' and 'port'"):
            utils._prepare_email(temp, '', None)

    create(['[smtp]', 'port=not-an-int'])
    with pytest.raises(ValueError, match='invalid literal for int()'):
        utils._prepare_email(temp, '', None)

    create(['[smtp]', 'host=smtp.example.com', 'port=25'])
    cfg = utils._prepare_email(temp, '', None)
    assert cfg == {'type': 'smtp', 'to': [''], 'from': '', 'host': 'smtp.example.com',
                   'port': 25, 'starttls': None, 'username': None, 'password': None}

    create(['[smtp]', 'host=h', 'port=1'])
    cfg = utils._prepare_email(temp, 'name', None)
    assert cfg == {'type': 'smtp', 'to': ['name'], 'from': 'name', 'host': 'h',
                   'port': 1, 'starttls': None, 'username': None, 'password': None}

    create(['[smtp]', 'host=h', 'port=1', 'domain=domain'])
    cfg = utils._prepare_email(temp, 'name', None)
    assert cfg == {'type': 'smtp', 'to': ['name@domain'], 'from': 'name@domain', 'host': 'h',
                   'port': 1, 'starttls': None, 'username': None, 'password': None}

    create(['[smtp]', 'host=h', 'port=1', 'domain=@domain'])
    cfg = utils._prepare_email(temp, ['name0', 'name1', 'name2'], None)
    assert cfg == {'type': 'smtp', 'to': ['name0@domain', 'name1@domain', 'name2@domain'],
                   'from': 'name0@domain', 'host': 'h', 'port': 1, 'starttls': None,
                   'username': None, 'password': None}

    create(['[smtp]', 'host=h', 'port=1', 'domain=@domain'])
    cfg = utils._prepare_email(temp, 'name@mail.com', None)
    assert cfg == {'type': 'smtp', 'to': ['name@mail.com'], 'from': 'name@mail.com',
                   'host': 'h', 'port': 1, 'starttls': None, 'username': None,
                   'password': None}

    create(['[smtp]', 'host=h', 'port=1', 'domain=@domain'])
    cfg = utils._prepare_email(temp, ['you@mail.com', 'me'], 'me')
    assert cfg == {'type': 'smtp', 'to': ['you@mail.com', 'me@domain'],
                   'from': 'me@domain', 'host': 'h', 'port': 1, 'starttls': None,
                   'username': None, 'password': None}

    for item in ('yes', 'YES', '1', 'true', 'True', 'on', 'On'):
        create(['[smtp]', 'host=h', 'port=1', 'starttls={}'.format(item)])
        cfg = utils._prepare_email(temp, 'you', 'me')
        assert cfg == {'type': 'smtp', 'to': ['you'], 'from': 'me', 'host': 'h',
                       'port': 1, 'starttls': True, 'username': None, 'password': None}

    for item in ('no', 'No', '0', 'false', 'False', 'off', 'Off'):
        create(['[smtp]', 'host=h', 'port=1', 'starttls={}'.format(item)])
        cfg = utils._prepare_email(temp, 'you', 'me')
        assert cfg == {'type': 'smtp', 'to': ['you'], 'from': 'me', 'host': 'h',
                       'port': 1, 'starttls': False, 'username': None, 'password': None}

    create(['[smtp]', 'host=h', 'port=1', 'username=user'])
    with pytest.raises(ValueError, match="Must specify the 'password'"):
        utils._prepare_email(temp, '', None)

    create(['[smtp]', 'host=h', 'port=1', 'password=pw'])
    with pytest.raises(ValueError, match="Must specify the 'username'"):
        utils._prepare_email(temp, '', None)

    create(['[smtp]', 'host=h', 'port=1', 'starttls=0', 'username=uname', 'password=pw'])
    cfg = utils._prepare_email(temp, 'you', 'me@mail')
    assert cfg == {'type': 'smtp', 'to': ['you'], 'from': 'me@mail', 'host': 'h',
                   'port': 1, 'starttls': False, 'username': 'uname', 'password': 'pw'}

    create(['[gmail]'])
    cfg = utils._prepare_email(temp, '', None)
    assert cfg == {'type': 'gmail', 'to': [''], 'from': 'me',
                   'account': None, 'credentials': None, 'scopes': None}
    cfg = utils._prepare_email(temp, 'me', None)
    assert cfg == {'type': 'gmail', 'to': ['me'], 'from': 'me',
                   'account': None, 'credentials': None, 'scopes': None}

    create(['[gmail]', 'domain=domain'])
    cfg = utils._prepare_email(temp, 'me', None)
    assert cfg == {'type': 'gmail', 'to': ['me'], 'from': 'me',
                   'account': None, 'credentials': None, 'scopes': None}

    create(['[gmail]', 'account=mine', 'domain=@gmail.com'])
    cfg = utils._prepare_email(temp, 'you', 'me')
    assert cfg == {'type': 'gmail', 'to': ['you@gmail.com'], 'from': 'me',
                   'account': 'mine', 'credentials': None, 'scopes': None}

    create(['[gmail]', 'credentials=path/to/oauth'])
    cfg = utils._prepare_email(temp, ['email@corp.com', 'me'], None)
    assert cfg == {'type': 'gmail', 'to': ['email@corp.com', 'me'], 'from': 'me',
                   'account': None, 'credentials': 'path/to/oauth', 'scopes': None}

    create(['[gmail]', 'credentials=path\\to\\oauth', 'account=work', 'domain=ignored'])
    cfg = utils._prepare_email(temp, 'name@gmail.com', 'name@email.com')
    assert cfg == {'type': 'gmail', 'to': ['name@gmail.com'], 'from': 'name@email.com',
                   'account': 'work', 'credentials': 'path\\to\\oauth', 'scopes': None}

    create(['[gmail]', 'credentials=path\\to\\oauth', 'account=work', 'domain=domain'])
    cfg = utils._prepare_email(temp, ['a', 'b', 'c@corp.net'], None)
    assert cfg == {'type': 'gmail', 'to': ['a@domain', 'b@domain', 'c@corp.net'],
                   'from': 'me', 'account': 'work', 'credentials': 'path\\to\\oauth',
                   'scopes': None}

    create(['[gmail]', 'scopes=a'])
    cfg = utils._prepare_email(temp, '', None)
    assert cfg == {'type': 'gmail', 'to': [''], 'from': 'me',
                   'account': None, 'credentials': None, 'scopes': ['a']}

    create(['[gmail]', 'scopes = ', ' gmail', ' gmail.send', ' g',
            ' gmail.metadata', '', '', '', 'account = work'])
    cfg = utils._prepare_email(temp, '', '')
    assert cfg == {'type': 'gmail', 'to': [''], 'from': 'me',
                   'account': 'work', 'credentials': None,
                   'scopes': ['gmail', 'gmail.send', 'g', 'gmail.metadata']}

    # file-like objects
    with open(temp, mode='rt') as fp:
        cfg = utils._prepare_email(fp, '', '')
        assert cfg == {'type': 'gmail', 'to': [''], 'from': 'me',
                       'account': 'work', 'credentials': None,
                       'scopes': ['gmail', 'gmail.send', 'g', 'gmail.metadata']}

    cfg = utils._prepare_email(StringIO('[gmail]'), '', None)
    assert cfg == {'type': 'gmail', 'to': [''], 'from': 'me',
                   'account': None, 'credentials': None, 'scopes': None}

    os.remove(temp)
