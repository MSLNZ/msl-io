import pytest
import numpy as np

from msl.io.dataset import Dataset


def test_instantiate():
    dset = Dataset(name='/data', parent=None, is_read_only=True, shape=(10, 10))
    assert dset.name == '/data'
    assert len(dset) == 10
    assert dset.size == 100
    assert dset.dtype == float
    assert dset.dtype.names is None

    dset = Dataset(name='dataset 1', parent=None, is_read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'dataset 1'
    assert len(dset) == 100
    assert dset.size == 100
    assert dset.dtype == int
    assert dset.dtype.names is None

    dset = Dataset(name='mixed', parent=None, is_read_only=True, shape=(100,), dtype=[('x', float), ('y', int), ('z', str)])
    assert dset.name == 'mixed'
    assert len(dset) == 100
    assert dset.size == 100
    assert len(dset['x']) == 100
    assert dset.dtype[0] == float
    assert len(dset['y']) == 100
    assert dset.dtype[1] == int
    assert len(dset['z']) == 100
    assert dset.dtype[2] == str
    assert dset.dtype.names == ('x', 'y', 'z')

    dset = Dataset(name='xxx', parent=None, is_read_only=True, data=[1, 2, 3])
    assert len(dset) == 3
    assert dset[0] == 1
    assert dset[1] == 2
    assert dset[2] == 3
    d = dset[:]
    assert len(d) == 3
    assert d[0] == 1
    assert d[1] == 2
    assert d[2] == 3
    d = dset[::2]
    assert len(d) == 2
    assert d[0] == 1
    assert d[1] == 3


def test_metadata():
    dset = Dataset(name='d', parent=None, is_read_only=False, shape=(100,),
                   dtype=int, order='F', temperature=21.3, lab='msl', x=-1)

    # 'name' is absorbed by Vertex
    # 'shape', 'dtype' and 'order' are kwargs that are absorbed by numpy

    assert len(dset.metadata) == 3
    assert dset.metadata['temperature'] == 21.3
    assert dset.metadata['lab'] == 'msl'
    assert dset.metadata['x'] == -1

    assert not dset.metadata.is_read_only

    dset.add_metadata(one=1, two=2, three=3)
    assert len(dset.metadata) == 6
    assert dset.metadata['one'] == 1
    assert dset.metadata['two'] == 2
    assert dset.metadata['three'] == 3


def test_field_access_as_attribute():
    # no names defined in the dtype
    dset = Dataset(name='data', parent=None, is_read_only=False, shape=(3, 3))
    assert len(dset) == 3
    assert dset.shape == (3, 3)
    assert dset.dtype == float
    assert dset.dtype.names is None

    with pytest.raises(AttributeError):
        _ = dset.there_are_no_field_names

    # names are defined in the dtype
    dset = Dataset(name='data', parent=None, is_read_only=False, shape=(100,),
                   dtype=[('x', float), ('y', int), ('z', str)])
    assert len(dset['x']) == 100
    assert len(dset.x) == 100
    assert len(dset['y']) == 100
    assert len(dset.y) == 100
    dset.y[:] = 1
    for val in dset.y:
        assert val == 1
    dset.x = np.arange(100, 200)
    assert np.array_equal(dset.x + dset.y, np.arange(101, 201))
    assert len(dset['z']) == 100
    assert len(dset.z) == 100
    assert dset['z'][0] == ''
    assert dset.z[0] == ''
    assert dset.dtype.names == ('x', 'y', 'z')


def test_read_only():
    dset = Dataset(name='my data', parent=None, is_read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'my data'
    assert len(dset) == 100
    assert dset.is_read_only
    assert dset.metadata.is_read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset[:] = 1

    # cannot modify data
    with pytest.raises(ValueError):
        dset[0] = 1

    # make writable
    dset.is_read_only = False
    assert not dset.is_read_only
    assert not dset.metadata.is_read_only

    # can modify data
    dset[:] = 1
    assert dset[0] == 1

    # make read only again
    dset.is_read_only = True
    assert dset.is_read_only
    assert dset.metadata.is_read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset[:] = 1

    # can make a dataset writeable but the metadata read-only
    dset.is_read_only = False
    assert not dset.is_read_only
    assert not dset.metadata.is_read_only
    dset.metadata.is_read_only = True
    assert not dset.is_read_only
    assert dset.metadata.is_read_only
    dset[:] = 1
    with pytest.raises(ValueError):
        dset.add_metadata(some_more_info=1)


def test_copy():
    orig = Dataset(name='abcdefg', parent=None, is_read_only=True, shape=(10,), dtype=int, voltage=1.2, current=5.3)

    assert orig.is_read_only
    assert orig.name == 'abcdefg'

    copy = orig.copy()
    assert isinstance(copy, Dataset)
    assert copy.is_read_only
    assert copy.metadata.is_read_only
    assert copy.name == 'abcdefg'
    for i in range(10):
        assert orig[i] == copy[i]
    assert orig.metadata['voltage'] == copy.metadata['voltage']
    assert orig.metadata['current'] == copy.metadata['current']

    copy.is_read_only = False

    assert not copy.is_read_only
    assert not copy.metadata.is_read_only
    assert orig.is_read_only
    assert orig.metadata.is_read_only

    val = 7 if orig[1] != 7 else 8
    copy[1] = val
    assert copy[1] == val
    assert orig[1] != copy[1]


def test_string_representation():
    dset = Dataset(name='abcd', parent=None, data=[[1, 2], [3, 4]], is_read_only=True, foo='bar')

    assert repr(dset) in ["<Dataset 'abcd' shape=(2, 2) dtype='<f8' (1 metadata)>",
                          "<Dataset 'abcd' shape=(2L, 2L) dtype='<f8' (1 metadata)>"]

    assert str(dset) == ('array([[1., 2.],\n'
                         '       [3., 4.]])')

    assert str(dset.metadata) == "<Metadata 'abcd' {'foo': 'bar'}>"

    # just for fun, test more index access
    assert dset[0, 0] + dset[0, 1] == 3
    assert all(dset[:, 0] + dset[:, 1] == [3, 7])
    assert all(dset[0, :] + dset[1, :] == [4, 6])


def test_ndarray_attribute():
    dset = Dataset(name='abcd', parent=None, data=[[1, 2], [3, 4]], is_read_only=True)

    as_list = dset.tolist()
    assert isinstance(as_list, list)
    assert dset.tolist() == [[1, 2], [3, 4]]
    assert dset.flatten().tolist() == [1, 2, 3, 4]

    assert dset.max() == 4
    assert dset.min() == 1
    assert all(dset.max(axis=1) == [2, 4])
    assert all(dset.max(axis=0) == [3, 4])


def test_scalar():
    dset = Dataset(name='abcd', parent=None, data=5, is_read_only=True)
    assert len(dset) == 1
    assert dset.shape == ()
    assert dset.size == 1
    assert dset.data == 5.0
