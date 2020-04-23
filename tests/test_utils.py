import os
import re
import hashlib
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
    path = os.path.join(os.path.dirname(__file__), 'samples', 'table.txt')
    sha256 = 'b9a4bbbcda4a3c826f0ec9b2dffda2cdbdbe9d7c078314c77daa36487f18c9a9'
    md5 = '371615396a440d36e29b0ec4a6a7a4f9'

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

    # use a bytes object
    data = buffer.getvalue()
    assert isinstance(data, bytes)
    assert sha256 == checksum(data, algorithm='sha256')
    assert md5 == checksum(data, algorithm='md5')

    # use a bytearray object
    byte_array = bytearray(data)
    assert sha256 == checksum(byte_array, algorithm='sha256')
    assert md5 == checksum(byte_array, algorithm='md5')

    # use a memoryview object
    assert sha256 == checksum(memoryview(data), algorithm='sha256')
    assert md5 == checksum(memoryview(data), algorithm='md5')

    # ensure that all available algorithms can be used
    for algorithm in hashlib.algorithms_available:
        value = checksum(b'data', algorithm=algorithm)
        assert isinstance(value, str)

    # invalid type
    with pytest.raises(TypeError):
        checksum(None)

    # unsupported algorithm
    with pytest.raises(ValueError, match=r'unsupported'):
        checksum(b'data', algorithm='invalid')


def test_get_basename():
    paths = [
        '/a/b/c/d/e/file.dat',
        'C:\\a\\b\\c\\d\\e\\file.dat',
        'file.dat',
        '/a/file.dat',
        r'C:\a\file.dat',
    ]
    for path in paths:
        assert get_basename(path) == 'file.dat'
        assert get_basename(path.encode()) == b'file.dat'

    assert get_basename(StringIO(u'hello')) == u'StringIO'
    assert get_basename(BytesIO(b'hello')) == 'BytesIO'

    with open(__file__, 'rt') as fp:
        assert get_basename(fp) == 'test_utils.py'
