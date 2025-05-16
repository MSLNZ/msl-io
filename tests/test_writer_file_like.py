"""
When a new Writer is created it should be added to the list of writers to test.
"""
import os
import tempfile
from io import BufferedWriter
from io import BytesIO
from io import StringIO
from io import TextIOWrapper

import numpy as np

try:
    import h5py
except ImportError:
    h5py = None

from msl.io import HDF5Writer
from msl.io import JSONWriter
from msl.io import read

# Append new Writers to test
writers = [JSONWriter, HDF5Writer]


def fill_root_with_data(root):
    root.add_metadata(x=1, foo="bar")
    b = root.create_group("a/b")
    b.create_dataset("points", data=[[1, 2], [3, 4], [-5, 6], [7, -8]], cartesian=True)
    root.a.add_metadata(two=2.0)


def assert_root_data(root):
    assert len(list(root.groups())) == 2
    assert len(list(root.descendants())) == 2
    assert len(list(root.ancestors())) == 0
    assert len(list(root.datasets())) == 1
    assert len(root.metadata) == 2
    assert root.metadata["x"] == 1
    assert root.metadata.foo == "bar"
    assert "a" in root
    assert "b" in root.a
    assert "points" in root.a.b
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
                assert isinstance(root.file, StringIO)
                assert repr(root) == f"<{writer.__name__} 'StringIO' (0 groups, 0 datasets, 0 metadata)>"
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == f"<{writer.__name__} 'StringIO' (2 groups, 1 datasets, 2 metadata)>"

            buf.seek(0)
            root2 = read(buf)
            assert isinstance(root2.file, StringIO)
            assert_root_data(root2)


def test_bytes_io():
    # write Root to a BytesIO stream and then read it back
    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with BytesIO() as buf:
            with writer(buf) as root:
                assert isinstance(root.file, BytesIO)
                assert repr(root) == f"<{writer.__name__} 'BytesIO' (0 groups, 0 datasets, 0 metadata)>"
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == f"<{writer.__name__} 'BytesIO' (2 groups, 1 datasets, 2 metadata)>"

            buf.seek(0)
            root2 = read(buf)
            assert isinstance(root2.file, BytesIO)
            assert_root_data(root2)


def test_open_text():
    # write Root to a text-io stream and then read it back
    path = os.path.join(tempfile.gettempdir(), "textfile.txt")
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer:
            continue  # The HDF5Writer cannot write to a text-based stream

        with open(path, mode="wt") as fp:
            with writer(fp) as root:
                assert isinstance(root.file, TextIOWrapper)
                assert repr(root) == f"<{writer.__name__} 'textfile.txt' (0 groups, 0 datasets, 0 metadata)>"
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == f"<{writer.__name__} 'textfile.txt' (2 groups, 1 datasets, 2 metadata)>"

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)

        os.remove(path)


def test_open_binary():
    # write Root to a binary-io stream and then read it back
    path = os.path.join(tempfile.gettempdir(), "binaryfile.bin")
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with open(path, mode="wb") as fp:
            with writer(fp) as root:
                assert isinstance(root.file, BufferedWriter)
                assert repr(root) == f"<{writer.__name__} 'binaryfile.bin' (0 groups, 0 datasets, 0 metadata)>"
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == f"<{writer.__name__} 'binaryfile.bin' (2 groups, 1 datasets, 2 metadata)>"

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)

        os.remove(path)
