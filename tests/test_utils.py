import os
import re
import sys
import stat
import uuid
import shutil
import hashlib
import tempfile
from io import BytesIO, StringIO

import pytest

from msl.io.utils import *
from msl.io.utils import get_basename


def test_search():

    def s(**kwargs):
        return list(search(base, **kwargs))

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

    sha1 = git_revision(root_dir)
    assert len(sha1) == 40
    assert all(char.isalnum() for char in sha1)

    sha1_short = git_revision(root_dir, short=True)
    assert len(sha1_short) > 0
    assert len(sha1_short) < len(sha1)
    assert sha1.startswith(sha1_short)

    # can specify any directory within the version control hierarchy
    assert git_revision(os.path.join(root_dir, '.git')) == sha1
    assert git_revision(os.path.join(root_dir, 'msl', 'examples', 'io')) == sha1
    assert git_revision(os.path.dirname(__file__)) == sha1
    assert git_revision(os.path.join(root_dir, 'docs', '_api')) == sha1


def test_checksum():
    path = os.path.join(os.path.dirname(__file__), 'samples', 'hdf5_sample.h5')
    sha256 = 'e5dad4f15335e603fd602c22bf9ddb71b3500f862905495d3d17e6159a463d2d'
    md5 = 'a46708df266595218db2ba06788c4695'

    # use a filename as a string
    assert isinstance(path, str)
    assert sha256 == checksum(path, algorithm='sha256')
    assert md5 == checksum(path, algorithm='md5')

    # use a filename as bytes
    path_as_bytes = path.encode()
    assert isinstance(path_as_bytes, bytes)
    assert sha256 == checksum(path_as_bytes, algorithm='sha256')
    assert md5 == checksum(path_as_bytes, algorithm='md5')

    # use a file pointer (binary mode)
    with open(path, 'rb') as fp:
        assert sha256 == checksum(fp, algorithm='sha256')
    with open(path, 'rb') as fp:
        assert md5 == checksum(fp, algorithm='md5')

    # use a byte buffer
    with open(path, 'rb') as fp:
        buffer = BytesIO(fp.read())
    assert buffer.tell() == 0
    assert sha256 == checksum(buffer, algorithm='sha256')
    assert buffer.tell() == 0
    assert md5 == checksum(buffer, algorithm='md5')
    assert buffer.tell() == 0

    # ensure that all available algorithms can be used
    for algorithm in hashlib.algorithms_available:
        value = checksum(path, algorithm=algorithm)
        assert isinstance(value, str)

    # file does not exist
    with pytest.raises(IOError, match='does_not_exist.txt'):
        checksum('/the/file/does_not_exist.txt')
    with pytest.raises(IOError, match='does_not_exist.txt'):
        checksum(b'/the/file/does_not_exist.txt')

    # invalid type
    with pytest.raises(TypeError):
        checksum(None)
    with pytest.raises(TypeError):
        checksum(bytearray(buffer.getvalue()))
    with pytest.raises(TypeError):
        checksum(memoryview(buffer.getvalue()))

    # unsupported algorithm
    with pytest.raises(ValueError, match=r'unsupported'):
        checksum(path, algorithm='invalid')


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
        assert get_basename(path) == 'file.dat'
        assert get_basename(path.encode()) == b'file.dat'

    assert get_basename(StringIO(u'hello')) == u'StringIO'
    assert get_basename(BytesIO(b'hello')) == 'BytesIO'

    with open(__file__, 'rt') as fp:
        assert get_basename(fp) == 'test_utils.py'


def test_copy():

    def check_stat(dest):
        src_stat = os.stat(__file__)
        dst_stat = os.stat(dest)
        for attr in dir(src_stat):
            if not attr.startswith('st_'):
                continue
            if attr in ['st_ino', 'st_ctime', 'st_ctime_ns']:  # these will never be equal
                continue
            src_value = getattr(src_stat, attr)
            dst_value = getattr(dst_stat, attr)
            if attr.endswith('time'):  # times can be approximate
                if abs(src_value - dst_value) > 1e-5:
                    return False
            elif src_value != dst_value:
                return False
        return True

    # make sure there is no remnant file from a previously-failed test
    if os.path.isfile(os.path.join(tempfile.gettempdir(), 'test_utils.py')):
        os.remove(os.path.join(tempfile.gettempdir(), 'test_utils.py'))

    # source file does not exist
    for item in [r'/the/file/does_not_exist.txt', r'/the/file/does_not_exist', r'does_not_exist']:
        with pytest.raises(IOError, match=item):
            copy(item, '')

    # destination invalid
    with pytest.raises(IOError, match=r"''"):
        copy(__file__, '')

    # copy (with metadata) to a directory that already exists
    dst = copy(__file__, tempfile.gettempdir())
    assert dst == os.path.join(tempfile.gettempdir(), 'test_utils.py')
    assert check_stat(dst)
    assert checksum(__file__) == checksum(dst)

    # destination already exists
    with pytest.raises(IOError, match=r'Will not overwrite'):
        copy(__file__, dst)
    with pytest.raises(IOError, match=r'Will not overwrite'):
        copy(__file__, tempfile.gettempdir())

    # can overwrite (with metadata), specify full path
    dst2 = copy(__file__, dst, overwrite=True)
    assert dst2 == dst
    assert check_stat(dst2)
    assert checksum(__file__) == checksum(dst2)

    # can overwrite (without metadata), specify full path
    dst3 = copy(__file__, dst, overwrite=True, include_metadata=False)
    assert dst3 == dst
    assert not check_stat(dst3)
    assert checksum(__file__) == checksum(dst3)

    # can overwrite (with metadata), specify directory only
    dst4 = copy(__file__, tempfile.gettempdir(), overwrite=True)
    assert dst4 == dst
    assert check_stat(dst4)
    assert checksum(__file__) == checksum(dst4)

    os.remove(dst)

    # copy without metadata
    dst = copy(__file__, tempfile.gettempdir(), include_metadata=False)
    assert dst == os.path.join(tempfile.gettempdir(), 'test_utils.py')
    assert not check_stat(dst)
    assert checksum(__file__) == checksum(dst)
    os.remove(dst)

    # copy (without metadata) but use a different destination basename
    destination = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + '.tmp')
    dst = copy(__file__, destination, include_metadata=False)
    assert dst == destination
    assert not check_stat(dst)
    assert checksum(__file__) == checksum(dst)
    os.remove(dst)

    # copy to a directory that does not exist
    new_dirs = str(uuid.uuid4()).split('-')
    assert not os.path.isdir(os.path.join(tempfile.gettempdir(), new_dirs[0]))
    destination = os.path.join(tempfile.gettempdir(), *new_dirs)
    destination = os.path.join(destination, 'new_file.tmp')
    dst = copy(__file__, destination)
    assert dst == destination
    assert check_stat(dst)
    assert checksum(__file__) == checksum(dst)
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

    remove_write_permissions(path)

    # the Read and Execute permissions are preserved
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == 'win32':
        assert mode == 0o444  # Windows does not have the Execute permission
    else:
        assert mode == 0o555

    # cannot open the file to modify it
    for mode in ['wb', 'ab', 'wt', 'at', 'w+', 'w+b']:
        with pytest.raises(IOError):
            open(path, mode)

    # cannot delete the file (only valid on Windows)
    if sys.platform == 'win32':
        with pytest.raises(OSError):
            os.remove(path)

    # can still read it
    with open(path, 'rb') as fp:
        assert fp.read() == b'hello world'

    # clean up by deleting the file
    os.chmod(path, 0o777)
    os.remove(path)
