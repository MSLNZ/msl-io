"""When a new Writer is created it should be added to the list of writers to test."""

import os
import tempfile
from io import StringIO

import numpy as np
import pytest

try:
    import h5py  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    h5py = None

from msl.io import Dataset, HDF5Writer, JSONWriter, Root, read

# Append new Writers to test
writers = [JSONWriter, HDF5Writer]


def fill_root_with_data(root: Root) -> None:
    root.add_metadata(x=1, foo="bar")
    b = root.create_group("a/b")
    _ = b.create_dataset("points", data=[[1, 2], [3, 4], [-5, 6], [7, -8]], cartesian=True)
    root.a.add_metadata(two=2.0)


def assert_root_data(root: Root) -> None:
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
    assert isinstance(points, Dataset)
    assert len(points.metadata) == 1
    assert points.metadata.cartesian
    assert isinstance(points.metadata.cartesian, (bool, np.bool_))
    assert points.shape == (4, 2)
    assert np.array_equal(points.max(), 7.0)
    assert np.array_equal(points.min(axis=0), [-5.0, -8.0])
    assert np.array_equal(points.max(axis=1), [2.0, 4.0, 6.0, 7.0])
    assert np.array_equal(points, [[1.0, 2.0], [3.0, 4.0], [-5.0, 6.0], [7.0, -8.0]])
    assert isinstance(points[0, 1], float)  # type: ignore[unreachable]


def test_none_type() -> None:
    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ValueError) as err:  # noqa: PT011, PT012, SIM117
            with writer() as root:
                assert root.file is None
                assert repr(root) == f"<{writer.__name__} 'NoneType' (0 groups, 0 datasets, 0 metadata)>"
        assert err.match("specify a file")


def test_file_path() -> None:
    # the URL is a string
    path = os.path.join(tempfile.gettempdir(), "foo")  # noqa: PTH118
    if os.path.isfile(path):  # noqa: PTH113
        os.remove(path)  # noqa: PTH107

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with writer(path) as root:
            assert root.file == path
            fill_root_with_data(root)
            assert_root_data(root)
            assert repr(root) == f"<{writer.__name__} 'foo' (2 groups, 1 dataset, 2 metadata)>"

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)
        os.remove(path)  # noqa: PTH107


def test_exception_raised() -> None:
    # the file gets written even if an exception is raised
    path = os.path.join(tempfile.gettempdir(), "bar")  # noqa: PTH118
    if os.path.isfile(path):  # noqa: PTH113
        os.remove(path)  # noqa: PTH107

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ZeroDivisionError):  # noqa: PT012, SIM117
            with writer(path) as root:
                assert root.file == path
                assert repr(root) == f"<{writer.__name__} 'bar' (0 groups, 0 datasets, 0 metadata)>"
                _ = 1 / 0

        root2 = read(path)
        assert root2.file == path
        assert len(root2.metadata) == 0
        assert len(list(root2.groups())) == 0
        assert len(list(root2.datasets())) == 0
        os.remove(path)  # noqa: PTH107

    for writer in writers:
        if writer is HDF5Writer and h5py is None:
            continue
        with pytest.raises(ZeroDivisionError):  # noqa: PT012, SIM117
            with writer(path) as root:
                assert root.file == path
                fill_root_with_data(root)
                assert_root_data(root)
                assert repr(root) == f"<{writer.__name__} 'bar' (2 groups, 1 dataset, 2 metadata)>"
                _ = 1 / 0

        root2 = read(path)
        assert root2.file == path
        assert_root_data(root2)
        os.remove(path)  # noqa: PTH107


def test_update_context_kwargs() -> None:
    with StringIO() as buf:
        with JSONWriter() as root:
            root.add_metadata(one=1)
            _ = root.create_dataset("dset", data=np.arange(9).reshape(3, 3))
            dtype_str = root.dset.dtype.str
            root.update_context_kwargs(file=buf, indent=None, separators=("|", ";"), sort_keys=True)
        file_info, value = buf.getvalue().splitlines()
        assert "MSL JSONWriter" in file_info
        assert value == '{"dset";{"data";[[0|1|2]|[3|4|5]|[6|7|8]]|"dtype";"%s"}|"one";1}' % dtype_str  # noqa: UP031
