import pytest

from msl.io.dataset import Dataset


def test_instantiate():
    dset = Dataset(name='/data', parent=None, is_read_only=True, shape=(10, 10))
    assert dset.name == '/data'
    assert len(dset.data) == 10
    assert dset.data.size == 100
    assert dset.data.dtype == float
    assert dset.data.dtype.names is None

    dset = Dataset(name='dataset 1', parent=None, is_read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'dataset 1'
    assert len(dset.data) == 100
    assert dset.data.size == 100
    assert dset.data.dtype == int
    assert dset.data.dtype.names is None

    dset = Dataset(name='mixed', parent=None, is_read_only=True, shape=(100,), dtype=[('x', float), ('y', int), ('z', str)])
    assert dset.name == 'mixed'
    assert len(dset.data) == 100
    assert dset.data.size == 100
    assert len(dset.data['x']) == 100
    assert dset.data.dtype[0] == float
    assert len(dset.data['y']) == 100
    assert dset.data.dtype[1] == int
    assert len(dset.data['z']) == 100
    assert dset.data.dtype[2] == str
    assert dset.data.dtype.names == ('x', 'y', 'z')

    dset = Dataset(name='xxx', parent=None, is_read_only=True, data=[1, 2, 3])
    assert len(dset.data) == 3
    assert dset.data[0] == 1
    assert dset.data[1] == 2
    assert dset.data[2] == 3


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
    assert len(dset.data) == 3
    assert dset.data.shape == (3, 3)
    assert dset.data.dtype == float
    assert dset.data.dtype.names is None
    with pytest.raises(AttributeError):
        _ = dset.data.there_are_no_field_names

    # names are defined in the dtype
    dset = Dataset(name='data', parent=None, is_read_only=False, shape=(100,),
                   dtype=[('x', float), ('y', int), ('z', str)])
    assert len(dset.data['x']) == 100
    assert len(dset.data.x) == 100
    assert len(dset.data['y']) == 100
    assert len(dset.data.y) == 100
    dset.data.y[:] = 1
    for val in dset.data.y:
        assert val == 1
    assert len(dset.data['z']) == 100
    assert len(dset.data.z) == 100
    assert dset.data['z'][0] == ''
    assert dset.data.z[0] == ''
    assert dset.data.dtype.names == ('x', 'y', 'z')


def test_read_only():
    dset = Dataset(name='my data', parent=None, is_read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'my data'
    assert len(dset.data) == 100
    assert dset.is_read_only
    assert dset.metadata.is_read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset.data[:] = 1

    # cannot modify data
    with pytest.raises(ValueError):
        dset.data[0] = 1

    # make writable
    dset.is_read_only = False
    assert not dset.is_read_only
    assert not dset.metadata.is_read_only

    # can modify data
    dset.data[:] = 1
    assert dset.data[0] == 1

    # make read only again
    dset.is_read_only = True
    assert dset.is_read_only
    assert dset.metadata.is_read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset.data[:] = 1

    # can make a dataset writeable but the metadata read-only
    dset.is_read_only = False
    assert not dset.is_read_only
    assert not dset.metadata.is_read_only
    dset.metadata.is_read_only = True
    assert not dset.is_read_only
    assert dset.metadata.is_read_only
    dset.data[:] = 1
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
        assert orig.data[i] == copy.data[i]
    assert orig.metadata['voltage'] == copy.metadata['voltage']
    assert orig.metadata['current'] == copy.metadata['current']

    copy.is_read_only = False

    assert not copy.is_read_only
    assert not copy.metadata.is_read_only
    assert orig.is_read_only
    assert orig.metadata.is_read_only

    copy.data[1] = 7
    assert copy.data[1] == 7
    assert orig.data[1] != copy.data[1]
