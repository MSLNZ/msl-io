import os
import re
import sys
import stat
import uuid
import shutil
import hashlib
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

    files = s(pattern=r'__init__\.py(?!c)', levels=None)
    assert len(files) == 6

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders='readers')
    assert len(files) == 5

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders=['readers', 'writers'])
    assert len(files) == 4

    files = s(pattern=r'authors')
    assert len(files) == 0

    files = s(pattern=r'authors', regex_flags=re.IGNORECASE)
    assert len(files) == 1

    files = s(pattern=r'setup')
    assert len(files) == 2

    files = s(pattern=r'README', levels=None)
    assert len(files) == 1

    files = s(pattern=r'README', levels=None, ignore_hidden_folders=False, exclude_folders=['.eggs', '.pytest_cache', '.cache'])
    assert len(files) == 1

    files = s(pattern=r'(^in|^auth)', levels=1, exclude_folders='htmlcov')
    assert len(files) == 3

    files = s(pattern=r'(^in|^auth)', levels=1, regex_flags=re.IGNORECASE, exclude_folders='htmlcov')
    assert len(files) == 4


def test_git_commit():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    sha1 = utils.git_revision(root_dir)
    assert len(sha1) == 40
    assert all(char.isalnum() for char in sha1)

    sha1_short = utils.git_revision(root_dir, short=True)
    assert len(sha1_short) > 0
    assert len(sha1_short) < len(sha1)
    assert sha1.startswith(sha1_short)

    # can specify any directory within the version control hierarchy
    assert utils.git_revision(os.path.join(root_dir, '.git')) == sha1
    assert utils.git_revision(os.path.join(root_dir, 'msl', 'examples', 'io')) == sha1
    assert utils.git_revision(os.path.dirname(__file__)) == sha1
    assert utils.git_revision(os.path.join(root_dir, 'docs', '_api')) == sha1

    # a directory not under version control
    assert utils.git_revision(tempfile.gettempdir()) is None


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
    with open(path, 'rb') as fp:
        assert sha256 == utils.checksum(fp, algorithm='sha256')
    with open(path, 'rb') as fp:
        assert md5 == utils.checksum(fp, algorithm='md5')

    # use a byte buffer
    with open(path, 'rb') as fp:
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

    with open(__file__, 'rt') as fp:
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
    with open(path, 'wb') as fp:
        fp.write(b'hello')

    # set to rwxrwxrwx
    os.chmod(path, 0o777)

    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        assert mode == 0o666  # Windows does not have the Execute permission
    else:
        assert mode == 0o777

    # can still modify it
    with open(path, 'ab') as fp:
        fp.write(b' world')
    with open(path, 'rb') as fp:
        assert fp.read() == b'hello world'

    utils.remove_write_permissions(path)

    # the Read and Execute permissions are preserved
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        assert mode == 0o444  # Windows does not have the Execute permission
    else:
        assert mode == 0o555

    # cannot open the file to modify it
    for mode in ['wb', 'ab', 'wt', 'at', 'w+', 'w+b']:
        with pytest.raises((IOError, OSError)):
            open(path, mode)

    # cannot delete the file (only valid on Windows)
    if sys.platform == 'win32':
        with pytest.raises(OSError):
            os.remove(path)

    # can still read it
    with open(path, 'rb') as fp:
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


@pytest.mark.skipif(os.name != 'nt', reason='non-Windows OS')
def test_run_as_admin():
    # Using verb=None as a keyword argument allows for testing the
    # 'run_as_admin' function without getting the UAC prompt,
    # but the test command must not require admin privileges.
    # Only test on Windows because the other cases:
    #   1) already and admin
    #   2) running on POSIX
    # are fairly straightforward implementations.

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

    # run a batch file with spaces in the file path and in the arguments
    file = os.path.join(tempfile.gettempdir(), 'msl io batch script.bat')
    with open(file, mode='w') as fp:
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
    with open(file, mode='w') as fp:
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
        utils.run_as_admin(args='sc create MSL-IO-TEST binPath= "C:\\hello world\\dummy.exe"', verb=None)
    with pytest.raises(PermissionError):
        utils.run_as_admin(args=['sc', 'create', 'MSL-IO-TEST', 'binPath=', 'C:\\hello world\\dummy.exe'], verb=None)
    with pytest.raises(OSError):
        utils.run_as_admin(args='doesnotexist.exe', verb=None)
