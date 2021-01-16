"""
When a new Writer is created is should be added to the list of writers to test.
"""
import os
import tempfile
from io import StringIO

import pytest
import numpy as np
try:
    import h5py
except ImportError:
    h5py = None

from msl.io import read, JSONWriter, HDF5Writer

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


def test_none_type():
    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ValueError) as err:
            with writer() as root:
                assert root.file is None
                assert repr(root) == "<{} 'NoneType' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
        assert err.match('specify a file')


def test_file_path():
    # the URL is a string
    path = os.path.join(tempfile.gettempdir(), 'foo')
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with writer(path) as root:
            assert root.file == path
            fill_root_with_data(root)
            assert_root_data(root)
            assert repr(root) == "<{} 'foo' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)
        os.remove(path)


def test_exception_raised():
    # the file gets written even if an exception is raised
    path = os.path.join(tempfile.gettempdir(), 'bar')
    if os.path.isfile(path):
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ZeroDivisionError):
            with writer(path) as root:
                assert root.file == path
                assert repr(root) == "<{} 'bar' (0 groups, 0 datasets, 0 metadata)>".format(writer.__name__)
                divide = 1/0

        root2 = read(path)
        assert root2.file == path
        assert len(root2.metadata) == 0
        assert len(list(root2.groups())) == 0
        assert len(list(root2.datasets())) == 0
        os.remove(path)

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ZeroDivisionError):
            with writer(path) as root:
                assert root.file == path
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == "<{} 'bar' (2 groups, 1 datasets, 2 metadata)>".format(writer.__name__)
                divide = 1/0

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)
        os.remove(path)


def test_update_context_kwargs():
    with StringIO() as buf:
        with JSONWriter() as root:
            root.add_metadata(one=1)
            root.create_dataset('dset', data=np.arange(9).reshape(3, 3))
            dtype_str = root.dset.dtype.str
            root.update_context_kwargs(file=buf, indent=None, separators=('|', ';'), sort_keys=True)
        file_info, value = buf.getvalue().splitlines()
        assert 'MSL JSONWriter' in file_info
        assert value == '{"dset";{"data";[[0|1|2]|[3|4|5]|[6|7|8]]|"dtype";"%s"}|"one";1}' % dtype_str
