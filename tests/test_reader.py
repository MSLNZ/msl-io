import os

import pytest

from msl.io.reader import Reader
from msl.io.root import Root


def test_get_root():
    root = Reader('').create_root()
    assert isinstance(root, Root)
    assert not root.is_read_only


def test_instantiate():
    reader = Reader('aaa.bbb')
    assert reader.url == 'aaa.bbb'


def test_get_lines():
    url = os.path.join(os.path.dirname(__file__), 'samples', 'test_file_for_static_Reader_methods')

    # get all 26 lines in order to use slicing to compare the results
    with open(url, 'r') as fp:
        all_lines = fp.read().split('\n')

    assert Reader.get_lines(url) == all_lines
    assert Reader.get_lines(url, None) == all_lines
    assert Reader.get_lines(url, 0) == all_lines[:0]
    assert Reader.get_lines(url, 0) == []
    assert Reader.get_lines(url, 1) == all_lines[:1]
    assert Reader.get_lines(url, -1) == all_lines[-1:]
    assert Reader.get_lines(url, 5) == all_lines[:5]
    assert Reader.get_lines(url, -5) == all_lines[-5:]
    assert Reader.get_lines(url, 100) == all_lines[:100]  # there are only 26 lines
    assert Reader.get_lines(url, 100) == all_lines
    assert Reader.get_lines(url, -100) == all_lines[-100:]
    assert Reader.get_lines(url, -100) == all_lines

    assert Reader.get_lines(url, None, None) == all_lines
    assert Reader.get_lines(url, None, 0) == all_lines[:0]
    assert Reader.get_lines(url, None, 0) == []
    assert Reader.get_lines(url, None, 1) == all_lines[:1]
    assert Reader.get_lines(url, None, -1) == all_lines[-1:]
    assert Reader.get_lines(url, None, 5) == all_lines[:5]
    assert Reader.get_lines(url, None, -5) == all_lines[-5:]
    assert Reader.get_lines(url, None, 100) == all_lines[:100]  # there are only 26 lines
    assert Reader.get_lines(url, None, 100) == all_lines
    assert Reader.get_lines(url, None, -100) == all_lines[-100:]
    assert Reader.get_lines(url, None, -100) == all_lines

    # if `start` is > 0 then we should subtract 1 from the `start` index in all_lines
    # because the first line is considered as `start`=1
    assert Reader.get_lines(url, 0, None) == []
    assert Reader.get_lines(url, 1, None) == all_lines[0:]
    assert Reader.get_lines(url, 1, None) == all_lines
    assert Reader.get_lines(url, -1, None) == all_lines[-1:]
    assert Reader.get_lines(url, 5, None) == all_lines[4:]
    assert Reader.get_lines(url, -5, None) == all_lines[-5:]
    assert Reader.get_lines(url, 100, None) == all_lines[99:]  # there are only 26 lines
    assert Reader.get_lines(url, 100, None) == []
    assert Reader.get_lines(url, -100, None) == all_lines[-100:]
    assert Reader.get_lines(url, -100, None) == all_lines

    # if `start` is > 0 then we should subtract 1 from the `start` index in all_lines
    # if `end` < -1 the we should add 1 so that the `end` line is included
    assert Reader.get_lines(url, 0, 0) == []
    assert Reader.get_lines(url, 1, 1) == all_lines[0:1]
    assert Reader.get_lines(url, 1, -1) == all_lines
    assert Reader.get_lines(url, 4, 8) == all_lines[3:8]
    assert Reader.get_lines(url, -8, -4) == all_lines[-8:-3]
    assert len(Reader.get_lines(url, -8, -4)) == 5
    assert Reader.get_lines(url, -4, -2) == all_lines[-4:-1]
    assert len(Reader.get_lines(url, -4, -2)) == 3
    assert Reader.get_lines(url, 2, 4) == all_lines[1:4]
    assert Reader.get_lines(url, -5, 4) == []
    assert Reader.get_lines(url, 4, -4) == all_lines[3:-3]
    assert Reader.get_lines(url, 100, 200) == []  # there are only 26 lines
    assert Reader.get_lines(url, -100, -50) == []
    assert Reader.get_lines(url, 25, 100) == all_lines[24:]

    assert len(Reader.get_lines(url)) == 26
    assert len(Reader.get_lines(url, remove_empty_lines=True)) == 24


def test_get_bytes():
    url = os.path.join(os.path.dirname(__file__), 'samples', 'test_file_for_static_Reader_methods')

    # get all 185 bytes in order to use slicing to compare the results
    with open(url, 'rb') as fp:
        all_bytes = fp.read()

    assert Reader.get_bytes(url) == all_bytes
    assert Reader.get_bytes(url, None) == all_bytes
    assert Reader.get_bytes(url, 0) == b''
    assert Reader.get_bytes(url, 1) == all_bytes[:1]
    assert len(Reader.get_bytes(url, 1)) == 1
    assert Reader.get_bytes(url, -1) == all_bytes[-1:]
    assert len(Reader.get_bytes(url, -1)) == 1
    assert Reader.get_bytes(url, 5) == all_bytes[:5]
    assert len(Reader.get_bytes(url, 5)) == 5
    assert Reader.get_bytes(url, -5) == all_bytes[-5:]
    assert len(Reader.get_bytes(url, -5)) == 5
    assert Reader.get_bytes(url, -50) == all_bytes[-50:]
    assert Reader.get_bytes(url, -5000) == all_bytes
    assert Reader.get_bytes(url, 5000) == all_bytes

    # if `end` < -1 then we must add 1 to include this byte
    assert Reader.get_bytes(url, None, None) == all_bytes
    assert Reader.get_bytes(url, None, 0) == b''
    assert Reader.get_bytes(url, None, -1) == all_bytes
    assert Reader.get_bytes(url, None, 1) == all_bytes[:1]
    assert Reader.get_bytes(url, None, -3) == all_bytes[:-2]
    assert Reader.get_bytes(url, None, 8) == all_bytes[:8]
    assert Reader.get_bytes(url, None, -123) == all_bytes[:-122]
    assert Reader.get_bytes(url, None, -5000) == all_bytes[:-5000]
    assert Reader.get_bytes(url, None, 5000) == all_bytes

    # if `start` > 0 then we must subtract 1 to include this byte
    assert Reader.get_bytes(url, 0, None) == all_bytes
    assert Reader.get_bytes(url, 1, None) == all_bytes
    assert Reader.get_bytes(url, -1, None) == all_bytes[-1:]
    assert len(Reader.get_bytes(url, -1, None)) == 1
    assert Reader.get_bytes(url, 5, None) == all_bytes[4:]
    assert Reader.get_bytes(url, 98, None) == all_bytes[97:]
    assert Reader.get_bytes(url, -50, None) == all_bytes[-50:]
    assert Reader.get_bytes(url, -5000, None) == all_bytes
    assert Reader.get_bytes(url, 5000, None) == b''

    # if `start` > 0 then we must subtract 1 to include this byte
    # if `end` < -1 then we must add 1 to include this byte
    assert Reader.get_bytes(url, 0, 0) == b''
    assert Reader.get_bytes(url, 1, 1) == all_bytes[0:1]
    assert Reader.get_bytes(url, 1, -1) == all_bytes
    assert Reader.get_bytes(url, 5, 10) == all_bytes[4:10]
    assert len(Reader.get_bytes(url, 5, 10)) == 6
    assert Reader.get_bytes(url, 3, -1) == all_bytes[2:]
    assert Reader.get_bytes(url, 123, -20) == all_bytes[122:-19]
    assert Reader.get_bytes(url, -123, 55) == all_bytes[-123:55]
    assert Reader.get_bytes(url, 33, 57) == all_bytes[32:57]
    assert Reader.get_bytes(url, -8, -4) == all_bytes[-8:-3]
    assert len(Reader.get_bytes(url, -8, -4)) == 5
    assert Reader.get_bytes(url, 600, -600) == all_bytes[599:-599]
    assert Reader.get_bytes(url, 600, -600) == b''
    assert Reader.get_bytes(url, 100, 50) == all_bytes[99:50]
    assert Reader.get_bytes(url, 100, 50) == b''
    assert Reader.get_bytes(url, 5000, 6000) == all_bytes[4999:6000]
    assert Reader.get_bytes(url, 5000, 6000) == b''
    assert Reader.get_bytes(url, -6000, -5000) == all_bytes[-6000:-4999]
    assert Reader.get_bytes(url, -6000, -5000) == b''

    assert Reader.get_bytes(url, 10, 1000, 100) == all_bytes[9:1000]  # the step size is not used


def test_get_extension():
    assert Reader.get_extension('') == ''
    assert Reader.get_extension('xxx') == ''
    assert Reader.get_extension('a.xxx') == '.xxx'
    assert Reader.get_extension('/home/msl/data.csv') == '.csv'
    assert Reader.get_extension('/home/msl/filename.with.dots.dat') == '.dat'


def test_override_methods():

    # the subclass must override this method
    with pytest.raises(NotImplementedError):
        Reader('').read()

    # the subclass must override this method
    assert not Reader('').can_read('')
