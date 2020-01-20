"""
When a new Writer is created is should be added to the list of writers to test.
"""
import os
import tempfile
from io import BytesIO, StringIO, TextIOWrapper, BufferedWriter

import numpy as np

from msl.io import read, JSONWriter, HDF5Writer
from msl.io.constants import IS_PYTHON2

# Append new Writers to test
writers = [JSONWriter, HDF5Writer]


def fill_root_with_data(root):
    root.add_metadata(x=1, foo='bar')
    b = root.create_group('a/b')
    b.create_dataset('points', data=[[1, 2], [3, 4], [-5, 6], [7, -8]], cartesian=True)
    root.a.add_metadata(two=2.0)


def assert_root_data(root):
    assert len(list(root.groups())) == 2
    assert len(list(root.descendants())) == 2
    assert len(list(root.ancestors())) == 0
    assert len(list(root.datasets())) == 1
    assert len(root.metadata) == 2
    assert root.metadata['x'] == 1
    assert root.metadata.foo == 'bar'
    assert 'a' in root
    assert 'b' in root.a
    assert 'points' in root.a.b
    assert len(root.a.metadata) == 1
    assert root.a.metadata.two == 2.0
    points = root.a.b.points
    assert len(points.metadata) == 1
    assert points.metadata.cartesian and isinstance(points.metadata.cartesian, (bool, np.bool_))
    assert points.shape == (4, 2)
    assert isinstance(points[0, 1], float)
    assert np.array_equal(points.max(), 7.0)
    assert np.array_equal(points.min(axis=0), [-5.0, -8.0])
    assert np.array_equal(points.max(axis=1), [2.0, 4.0, 6.0, 7.0])
    assert np.array_equal(points, [[1.0, 2.0], [3.0, 4.0], [-5.0, 6.0], [7.0, -8.0]])


def test_string_io():
    # write Root to a StringIO stream and then read it back
    for writer in writers:
        if writer is HDF5Writer:
            continue  # The HDF5Writer cannot write to a text-based stream

        with StringIO() as buf:
            with writer(buf) as root:
                assert isinstance(root.url, StringIO)
                assert repr(root) == "<{} 'StringIO' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == "<{} 'StringIO' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)

            buf.seek(0)
            root2 = read(buf)
            assert isinstance(root2.url, StringIO)
            assert_root_data(root2)


def test_bytes_io():
    # write Root to a BytesIO stream and then read it back
    for writer in writers:
        with BytesIO() as buf:
            with writer(buf) as root:
                assert isinstance(root.url, BytesIO)
                assert repr(root) == "<{} 'BytesIO' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == "<{} 'BytesIO' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)

            buf.seek(0)
            root2 = read(buf)
            assert isinstance(root2.url, BytesIO)
            assert_root_data(root2)


def test_open_text():
    # write Root to a text-io stream and then read it back
    path = os.path.join(tempfile.gettempdir(), 'textfile.txt')
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer:
            continue  # The HDF5Writer cannot write to a text-based stream

        with open(path, 'wt') as fp:
            with writer(fp) as root:
                if IS_PYTHON2:
                    assert isinstance(root.url, file)
                else:
                    assert isinstance(root.url, TextIOWrapper)
                assert repr(root) == "<{} 'textfile.txt' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == "<{} 'textfile.txt' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)

        root2 = read(path)
        assert root2.url == path
        assert_root_data(root2)

        os.remove(path)


def test_open_binary():
    # write Root to a binary-io stream and then read it back
    path = os.path.join(tempfile.gettempdir(), 'binaryfile.bin')
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        with open(path, 'wb') as fp:
            with writer(fp) as root:
                if IS_PYTHON2:
                    assert isinstance(root.url, file)
                else:
                    assert isinstance(root.url, BufferedWriter)
                assert repr(root) == "<{} 'binaryfile.bin' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == "<{} 'binaryfile.bin' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)

        root2 = read(path)
        assert root2.url == path
        assert_root_data(root2)

        os.remove(path)
