import sys

import pytest
import numpy as np

from msl.io.dataset import Dataset


def test_instantiate():
    dset = Dataset(name='/data', parent=None, read_only=True, shape=(10, 10))
    assert dset.name == '/data'
    assert len(dset) == 10
    assert dset.size == 100
    assert dset.dtype == float
    assert dset.dtype.names is None

    dset = Dataset(name='dataset 1', parent=None, read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'dataset 1'
    assert len(dset) == 100
    assert dset.size == 100
    assert dset.dtype == int
    assert dset.dtype.names is None

    dset = Dataset(name='mixed', parent=None, read_only=True, shape=(100,), dtype=[('x', float), ('y', int), ('z', str)])
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

    dset = Dataset(name='xxx', parent=None, read_only=True, data=[1, 2, 3])
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
    dset = Dataset(name='d', parent=None, read_only=False, shape=(100,),
                   dtype=int, order='F', temperature=21.3, lab='msl', x=-1)

    # 'name' is absorbed by Vertex
    # 'shape', 'dtype' and 'order' are kwargs that are absorbed by numpy

    assert len(dset.metadata) == 3
    assert dset.metadata['temperature'] == 21.3
    assert dset.metadata['lab'] == 'msl'
    assert dset.metadata['x'] == -1

    assert not dset.metadata.read_only

    dset.add_metadata(one=1, two=2, three=3)
    assert len(dset.metadata) == 6
    assert dset.metadata['one'] == 1
    assert dset.metadata['two'] == 2
    assert dset.metadata['three'] == 3


def test_field_access_as_attribute():
    # no names defined in the dtype
    dset = Dataset(name='data', parent=None, read_only=False, shape=(3, 3))
    assert len(dset) == 3
    assert dset.shape == (3, 3)
    assert dset.dtype == float
    assert dset.dtype.names is None

    with pytest.raises(AttributeError):
        _ = dset.there_are_no_field_names

    # names are defined in the dtype
    dset = Dataset(name='data', parent=None, read_only=False, shape=(100,),
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
    dset = Dataset(name='my data', parent=None, read_only=True, shape=(100,), dtype=int)
    assert dset.name == 'my data'
    assert len(dset) == 100
    assert dset.read_only
    assert dset.metadata.read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset[:] = 1

    # cannot modify data
    with pytest.raises(ValueError):
        dset[0] = 1

    # make writable
    dset.read_only = False
    assert not dset.read_only
    assert not dset.metadata.read_only

    # can modify data
    dset[:] = 1
    assert dset[0] == 1

    # make read only again
    dset.read_only = True
    assert dset.read_only
    assert dset.metadata.read_only

    # cannot modify data
    with pytest.raises(ValueError):
        dset[:] = 1

    # can make a dataset writeable but the metadata read-only
    dset.read_only = False
    assert not dset.read_only
    assert not dset.metadata.read_only
    dset.metadata.read_only = True
    assert not dset.read_only
    assert dset.metadata.read_only
    dset[:] = 1
    with pytest.raises(ValueError):
        dset.add_metadata(some_more_info=1)


def test_copy():
    orig = Dataset(name='abcdefg', parent=None, read_only=True, shape=(10,), dtype=int, voltage=1.2, current=5.3)

    assert orig.read_only
    assert orig.name == 'abcdefg'

    copy = orig.copy()
    assert isinstance(copy, Dataset)
    assert copy.read_only
    assert copy.metadata.read_only
    assert copy.name == 'abcdefg'
    for i in range(10):
        assert orig[i] == copy[i]
    assert orig.metadata['voltage'] == copy.metadata['voltage']
    assert orig.metadata['current'] == copy.metadata['current']

    copy.read_only = False

    assert not copy.read_only
    assert not copy.metadata.read_only
    assert orig.read_only
    assert orig.metadata.read_only

    val = 7 if orig[1] != 7 else 8
    copy[1] = val
    assert copy[1] == val
    assert orig[1] != copy[1]


def test_string_representation():
    dset = Dataset(name='abcd', parent=None, data=[[1, 2], [3, 4]], read_only=True, foo='bar')

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
    dset = Dataset(name='abcd', parent=None, data=[[1, 2], [3, 4]], read_only=True)

    as_list = dset.tolist()
    assert isinstance(as_list, list)
    assert dset.tolist() == [[1, 2], [3, 4]]
    assert dset.flatten().tolist() == [1, 2, 3, 4]

    assert dset.max() == 4
    assert dset.min() == 1
    assert all(dset.max(axis=1) == [2, 4])
    assert all(dset.max(axis=0) == [3, 4])


def test_scalar():
    dset = Dataset(name='abcd', parent=None, data=5, read_only=True)
    assert len(dset) == 1
    assert dset.shape == ()
    assert dset.size == 1
    assert dset.data == 5.0


def test_add():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 + rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([5., 7., 9.]))

    for lhs in ([4, 5, 6], d2):
        result = lhs + d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([5., 7., 9.]))


def test_sub():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 - rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([-3., -3., -3.]))

    for lhs in ([4, 5, 6], d2):
        result = lhs - d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([3., 3., 3.]))


def test_mul():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 * rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([4., 10., 18.]))

    for lhs in ([4, 5, 6], d2):
        result = lhs * d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([4., 10., 18.]))


def test_truediv():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 1])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 4, 10])

    for rhs in ([4., 4., 10.], d2):
        result = d1 / rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0.25, 0.5, 0.1]))

    for lhs in ([4., 4., 10.], d2):
        result = lhs / d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([4., 2., 10.]))


def test_floordiv():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1e3, 1e4, 1e5])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[1e2, 1e3, 1e4])

    for rhs in ([1e2, 1e3, 1e4], d2):
        result = d1 // rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([10., 10., 10.]))

    for lhs in ([1e2, 1e3, 1e4], d2):
        result = lhs // d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0., 0., 0.]))


def test_pow():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    result = d1 ** 3
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([1., 8., 27.]))

    result = pow(d1, 3)
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([1., 8., 27.]))

    result = 3 ** d1
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([3., 9., 27.]))

    result = pow(3, d1)
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([3., 9., 27.]))

    for rhs in ([4., 5., 6.], d2):
        result = d1 ** rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([1., 32., 729.]))

        result = pow(d1, rhs)
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([1., 32., 729.]))

    for lhs in ([4., 5., 6.], d2):
        result = lhs ** d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([4., 25., 216.]))

        result = pow(lhs, d1)
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([4., 25., 216.]))


@pytest.mark.skipif(sys.version_info[:2] < (3, 5), reason='the @ operator requires Python 3.5+')
def test_matmul():
    import dataset_matmul
    dataset_matmul.run()


def test_mod():
    d = Dataset(name='/d', parent=None, read_only=True, data=list(range(7)))

    result = d % 5
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([0, 1, 2, 3, 4, 0, 1]))

    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[4, 7])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[2, 3])

    for rhs in ([2, 3], d2):
        result = d1 % rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0, 1]))

    for lhs in ([2, 3], d2):
        result = lhs % d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([2, 3]))


def test_divmod():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[3, 7, 12, 52, 62])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.arange(1, 6))

    for rhs in ([1, 2, 3, 4, 5], d2):
        div, mod = divmod(d1, rhs)
        assert isinstance(div, np.ndarray)
        assert np.array_equal(div, np.array([3,  3,  4, 13, 12]))
        assert isinstance(mod, np.ndarray)
        assert np.array_equal(mod, np.array([0, 1, 0, 0, 2]))

    for lhs in ([1, 2, 3, 4, 5], d2):
        div, mod = divmod(lhs, d1)
        assert isinstance(div, np.ndarray)
        assert np.array_equal(div, np.array([0, 0, 0, 0, 0]))
        assert isinstance(mod, np.ndarray)
        assert np.array_equal(mod, np.array([1, 2, 3, 4, 5]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.arange(5))
    div, mod = divmod(d, 3)
    assert isinstance(div, np.ndarray)
    assert np.array_equal(div, np.array([0, 0, 0, 1, 1]))
    assert isinstance(mod, np.ndarray)
    assert np.array_equal(mod, np.array([0, 1, 2, 0, 1]))


def test_lshift():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=np.array([1, 2, 3, 4, 5]))
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.array([3, 7, 11, 15, 19]))

    result = d1 << 1
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([2, 4, 6, 8, 10]))

    result = 1 << d1
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([2, 4, 8, 16, 32]))

    for rhs in ([3, 7, 11, 15, 19], d2):
        result = d1 << rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([8, 256, 6144, 131072, 2621440]))

    for lhs in ([3, 7, 11, 15, 19], d2):
        result = lhs << d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([6, 28, 88, 240, 608]))


def test_rshift():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=np.array([1, 2, 3, 4, 5]))
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.array([3, 7, 12, 52, 62]))

    result = d1 >> 10
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([0, 0, 0, 0, 0]))

    result = 10 >> d1
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([5, 2, 1, 0, 0]))

    for rhs in ([3, 7, 12, 52, 62], d2):
        result = d1 >> rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0, 0, 0, 0, 0]))

    for lhs in ([3, 7, 12, 52, 62], d2):
        result = lhs >> d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([1, 1, 1, 3, 1]))


def test_and():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 & rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0, 1, 0, 1, 4, 5, 0, 1, 0]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs & d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([0, 1, 0, 1, 4, 5, 0, 1, 0]))


def test_xor():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 ^ rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([10, 10, 14, 14, 10, 10, 22, 22, 26]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs ^ d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([10, 10, 14, 14, 10, 10, 22, 22, 26]))


def test_or():
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 | rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([10, 11, 14, 15, 14, 15, 22, 23, 26]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs | d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([10, 11, 14, 15, 14, 15, 22, 23, 26]))


def test_neg():
    # unary "-"

    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    for rhs in [[4, 5, 6], d2]:
        result = -d1 + rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([3, 3, 3]))


def test_pos():
    # unary "+"

    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name='/d2', parent=None, read_only=True, data=[4, 5, 6])

    for rhs in [[4, 5, 6], d2]:
        result = +d1 - rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([-3, -3, -3]))


def test_abs():
    # unary "abs()"

    d = Dataset(name='/d', parent=None, read_only=True, data=[1, -2, 3, -4])

    result = abs(d)
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([1, 2, 3, 4]))


def test_invert():
    # unary "~"

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, -2, 3, -4]))

    result = ~d
    assert isinstance(result, np.ndarray)
    assert np.array_equal(result, np.array([-2, 1, -4, 3]))


def test_assignments():
    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d += 1
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([2, 3, 4]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d -= 1
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([0, 1, 2]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d *= 10
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([10, 20, 30]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([10, 20, 30]))
    d /= 10
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([1, 2, 3]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([10, 20, 30]))
    d //= 5
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([2, 4, 6]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([10, 20, 30]))
    d %= 15
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([10, 5, 0]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d **= 3
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([1, 8, 27]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d <<= 3
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([8, 16, 24]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([10, 20, 30]))
    d >>= 2
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([2, 5, 7]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d &= 2
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([0, 2, 2]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d ^= 2
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([3, 0, 1]))

    d = Dataset(name='/d', parent=None, read_only=True, data=np.array([1, 2, 3]))
    d |= 2
    assert isinstance(d, np.ndarray)
    assert np.array_equal(d, np.array([3, 2, 3]))


def test_numpy_function():
    # np.xxx() is also valid syntax with a Dataset

    array = np.array([1, 2, 3])
    d1 = Dataset(name='/d1', parent=None, read_only=True, data=[1, 2, 3])

    cos = np.cos(d1)
    assert isinstance(cos, np.ndarray)
    assert np.array_equal(cos, np.cos(array))

    sqrt = np.sqrt(d1)
    assert isinstance(sqrt, np.ndarray)
    assert np.array_equal(sqrt, np.sqrt(array))

    abs_ = np.abs(d1)
    assert isinstance(abs_, np.ndarray)
    assert np.array_equal(abs_, np.abs(array))

    max_ = np.max(d1)
    assert isinstance(max_, float)
    assert np.array_equal(max_, np.max(array))
