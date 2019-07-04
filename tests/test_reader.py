import os

import pytest

from msl.io import Reader
from msl.io.base_io import Root


def test_get_root():
    root = Reader('')
    assert isinstance(root, Root)
    assert not root.is_read_only


def test_instantiate():
    reader = Reader('aaa.bbb')
    assert reader.url == 'aaa.bbb'


def test_get_lines():
    url = os.path.join(os.path.dirname(__file__), 'samples', 'test_file_for_static_Reader_lines')

    # the file contains 26 lines
    with open(url, 'r') as fp:
        all_lines = fp.read().split('\n')

    assert len(Reader.get_lines(url)) == 26
    assert len(Reader.get_lines(url, remove_empty_lines=True)) == 24

    assert Reader.get_lines(url) == all_lines
    assert Reader.get_lines(url, None) == all_lines
    assert Reader.get_lines(url, 0) == []
    assert Reader.get_lines(url, 1) == ['line1']
    assert Reader.get_lines(url, -1) == ['line26']
    assert Reader.get_lines(url, 5) == ['line1', 'line2', 'line3', 'line4', 'line5']
    assert Reader.get_lines(url, -5) == ['line22', 'line23', 'line24', 'line25', 'line26']
    assert Reader.get_lines(url, 100) == all_lines
    assert Reader.get_lines(url, -100) == all_lines

    assert Reader.get_lines(url, None, None) == all_lines
    assert Reader.get_lines(url, None, 0) == []
    assert Reader.get_lines(url, None, 1) == ['line1']
    assert Reader.get_lines(url, None, -1) == all_lines
    assert Reader.get_lines(url, None, 5) == ['line1', 'line2', 'line3', 'line4', 'line5']
    assert Reader.get_lines(url, None, -20) == ['line1', 'line2', 'line3', 'line4', 'line5', 'line6', 'line7']
    assert Reader.get_lines(url, None, 100) == all_lines
    assert Reader.get_lines(url, None, -100) == []

    assert Reader.get_lines(url, 0, None) == all_lines
    assert Reader.get_lines(url, 1, None) == all_lines
    assert Reader.get_lines(url, -1, None) == ['line26']
    assert Reader.get_lines(url, 18, None) == ['line18', 'line19', 'line20', '', 'line22',
                                               'line23', 'line24', 'line25', 'line26']
    assert Reader.get_lines(url, -5, None) == ['line22', 'line23', 'line24', 'line25', 'line26']
    assert Reader.get_lines(url, 100, None) == []  # there are only 26 lines
    assert Reader.get_lines(url, -100, None) == all_lines

    assert Reader.get_lines(url, 0, 0) == []
    assert Reader.get_lines(url, 1, 1) == ['line1']
    assert Reader.get_lines(url, 1, -1) == all_lines
    assert Reader.get_lines(url, 4, 8) == ['line4', 'line5', 'line6', 'line7', 'line8']
    assert Reader.get_lines(url, -8, -4) == ['line19', 'line20', '', 'line22', 'line23']
    assert Reader.get_lines(url, 2, 4) == ['line2', 'line3', 'line4']
    assert Reader.get_lines(url, -5, 4) == []
    assert Reader.get_lines(url, 10, -7) == ['line10', '', 'line12', 'line13', 'line14', 'line15',
                                             'line16', 'line17', 'line18', 'line19', 'line20']
    assert Reader.get_lines(url, 100, 200) == []  # there are only 26 lines
    assert Reader.get_lines(url, -100, -50) == []
    assert Reader.get_lines(url, 25, 100) == ['line25', 'line26']

    assert Reader.get_lines(url, 1, -1, 6) == ['line1', 'line7', 'line13', 'line19', 'line25']
    assert Reader.get_lines(url, 0, None, 6) == ['line1', 'line7', 'line13', 'line19', 'line25']
    assert Reader.get_lines(url, None, None, 6) == ['line1', 'line7', 'line13', 'line19', 'line25']
    assert Reader.get_lines(url, 1, 15, 6) == ['line1', 'line7', 'line13']
    assert Reader.get_lines(url, -20, -5, 5) == ['line7', 'line12', 'line17', 'line22']
    assert Reader.get_lines(url, -100, -21, 2) == ['line1', 'line3', 'line5']
    assert Reader.get_lines(url, -100, -20, 2) == ['line1', 'line3', 'line5', 'line7']
    assert Reader.get_lines(url, 15, 25, 3) == ['line15', 'line18', '', 'line24']
    assert Reader.get_lines(url, 15, 25, 3, remove_empty_lines=True) == ['line15', 'line18', 'line24']


def test_get_bytes():
    url = os.path.join(os.path.dirname(__file__), 'samples', 'test_file_for_static_Reader_bytes')

    # the file contains 184 bytes
    with open(url, 'rb') as fp:
        all_bytes = fp.read()

    assert Reader.get_bytes(url) == all_bytes
    assert Reader.get_bytes(url, None) == all_bytes
    assert Reader.get_bytes(url, 0) == b''
    assert Reader.get_bytes(url, 1) == b'!'
    assert Reader.get_bytes(url, -1) == b'~'
    assert Reader.get_bytes(url, 7) == b'!"#$%&('
    assert Reader.get_bytes(url, -5) == b'z{|}~'
    assert Reader.get_bytes(url, -21) == b'jklmnopqrstuvwxyz{|}~'
    assert Reader.get_bytes(url, -5000) == all_bytes
    assert Reader.get_bytes(url, 5000) == all_bytes

    assert Reader.get_bytes(url, None, None) == all_bytes
    assert Reader.get_bytes(url, None, 0) == b''
    assert Reader.get_bytes(url, None, -1) == all_bytes
    assert Reader.get_bytes(url, None, 1) == b'!'
    assert Reader.get_bytes(url, None, -179) == b'!"#$%&'  # 184 - 179 -> the first 6 bytes
    assert Reader.get_bytes(url, None, 8) == b'!"#$%&()'
    assert Reader.get_bytes(url, None, -5000) == b''
    assert Reader.get_bytes(url, None, 5000) == all_bytes

    assert Reader.get_bytes(url, 0, None) == all_bytes
    assert Reader.get_bytes(url, 1, None) == all_bytes
    assert Reader.get_bytes(url, -1, None) == b'~'
    assert Reader.get_bytes(url, 123, None) == b'@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~'
    assert Reader.get_bytes(url, -37, None) == b'YZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~'
    assert Reader.get_bytes(url, -5000, None) == all_bytes
    assert Reader.get_bytes(url, 5000, None) == b''

    assert Reader.get_bytes(url, 0, 0) == b''
    assert Reader.get_bytes(url, 1, 1) == b'!'
    assert Reader.get_bytes(url, 1, -1) == all_bytes
    assert Reader.get_bytes(url, 5, 10) == b'%&()*+'
    assert Reader.get_bytes(url, 139, -1) == b'PQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~'
    assert Reader.get_bytes(url, 123, -20) == b'@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijk'
    assert Reader.get_bytes(url, -101, 55) == b''
    assert Reader.get_bytes(url, 33, 57) == b'BCDEFGHIJKLMNOPQRSTUVWXYZ'
    assert Reader.get_bytes(url, -10, -4) == b'uvwxyz{'
    assert Reader.get_bytes(url, 600, -600) == b''
    assert Reader.get_bytes(url, 100, 50) == b''
    assert Reader.get_bytes(url, 5000, 6000) == b''
    assert Reader.get_bytes(url, -6000, -5000) == b''

    assert Reader.get_bytes(url, 0, 6, 3) == b'!$'
    assert Reader.get_bytes(url, 1, 6, 3) == b'!$'
    assert Reader.get_bytes(url, 0, 7, 3) == b'!$('
    assert Reader.get_bytes(url, 1, 7, 3) == b'!$('
    assert Reader.get_bytes(url, 0, 8, 3) == b'!$('
    assert Reader.get_bytes(url, 1, 8, 3) == b'!$('
    assert Reader.get_bytes(url, 0, 12, 3) == b'!$(+'
    assert Reader.get_bytes(url, 1, 12, 3) == b'!$(+'
    assert Reader.get_bytes(url, 0, 13, 3) == b'!$(+.'
    assert Reader.get_bytes(url, 1, 13, 3) == b'!$(+.'
    assert Reader.get_bytes(url, 9, 49, 8) == b'*2:BJR'
    assert Reader.get_bytes(url, 9, 53, 8) == b'*2:BJR'
    assert Reader.get_bytes(url, -19, -5, 5) == b'lqv'
    assert Reader.get_bytes(url, -19, -4, 5) == b'lqv{'
    assert Reader.get_bytes(url, -10, -1, 2) == b'uwy{}'
    assert Reader.get_bytes(url, -11, -1, 2) == b'tvxz|~'
    assert Reader.get_bytes(url, -200, -155, 5) == b'!&,16;'
    assert Reader.get_bytes(url, 109, 500, 10) == b'2<FPZeoy'


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
