import numpy as np
import pytest

from msl.io import Dataset, Root
from msl.io.metadata import Metadata


def test_instantiate() -> None:
    dset = Dataset(name="/data", parent=None, read_only=True, shape=(10, 10))
    assert dset.name == "/data"
    assert len(dset) == 10
    assert dset.size == 100
    assert dset.dtype == float
    assert dset.dtype.names is None

    dset = Dataset(name="dataset 1", parent=None, read_only=True, shape=(100,), dtype=int)
    assert dset.name == "dataset 1"
    assert len(dset) == 100
    assert dset.size == 100
    assert dset.dtype == int
    assert dset.dtype.names is None

    dset = Dataset(
        name="mixed", parent=None, read_only=True, shape=(100,), dtype=[("x", float), ("y", int), ("z", str)]
    )
    assert dset.name == "mixed"
    assert len(dset) == 100
    assert dset.size == 100
    assert len(dset["x"]) == 100
    assert dset.dtype[0] is np.dtype(np.float64)
    assert len(dset["y"]) == 100
    assert dset.dtype[1] is np.dtype(np.int64)
    assert len(dset["z"]) == 100
    assert dset.dtype[2] is np.dtype("<U")
    assert dset.dtype.names == ("x", "y", "z")

    dset = Dataset(name="xxx", parent=None, read_only=True, data=[1, 2, 3])
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


def test_metadata() -> None:
    dset = Dataset(
        name="d", parent=None, read_only=False, shape=(100,), dtype=int, order="F", temperature=21.3, lab="msl", x=-1
    )

    # 'name' is absorbed by Vertex
    # 'shape', 'dtype' and 'order' are kwargs that are absorbed by numpy

    assert len(dset.metadata) == 3
    assert dset.metadata["temperature"] == 21.3
    assert dset.metadata["lab"] == "msl"
    assert dset.metadata["x"] == -1

    assert not dset.metadata.read_only

    dset.add_metadata(one=1, two=2, three=3)
    assert len(dset.metadata) == 6
    assert dset.metadata["one"] == 1
    assert dset.metadata["two"] == 2
    assert dset.metadata["three"] == 3


def test_field_access_as_attribute() -> None:
    # no names defined in the dtype
    dset = Dataset(name="data", parent=None, read_only=False, shape=(3, 3))
    assert len(dset) == 3
    assert dset.shape == (3, 3)
    assert dset.dtype == float
    assert dset.dtype.names is None

    with pytest.raises(AttributeError):
        _ = dset.there_are_no_field_names

    # names are defined in the dtype
    dset = Dataset(
        name="data", parent=None, read_only=False, shape=(100,), dtype=[("x", float), ("y", int), ("z", str)]
    )
    assert len(dset["x"]) == 100
    assert len(dset.x) == 100
    assert len(dset["y"]) == 100
    assert len(dset.y) == 100
    dset.y[:] = 1
    for val in dset.y:
        assert val == 1
    dset.x = np.arange(100, 200)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
    assert np.array_equal(dset.x + dset.y, np.arange(101, 201))
    assert len(dset["z"]) == 100
    assert len(dset.z) == 100
    assert dset["z"][0] == ""
    assert dset.z[0] == ""
    assert dset.dtype.names == ("x", "y", "z")


def test_read_only() -> None:
    dset = Dataset(name="my data", parent=None, read_only=True, shape=(100,), dtype=int)
    assert dset.name == "my data"
    assert len(dset) == 100
    assert dset.read_only
    assert dset.metadata.read_only

    # cannot modify data
    with pytest.raises(ValueError, match="read-only"):
        dset[:] = 1
    with pytest.raises(ValueError, match="read-only"):
        dset[0] = 1
    with pytest.raises(ValueError, match="read-only"):
        dset += 1

    # make writable
    dset.read_only = False
    assert not dset.read_only
    assert not dset.metadata.read_only

    # can modify data
    dset[:] = 1  # type: ignore[unreachable]
    assert np.array_equal(dset, np.ones(100))

    # make read only again
    dset.read_only = True
    assert dset.read_only
    assert dset.metadata.read_only

    # cannot modify data
    with pytest.raises(ValueError, match="read-only"):
        dset[:] = 1

    # can make a dataset writeable but the metadata read-only
    dset.read_only = False
    assert not dset.read_only
    assert not dset.metadata.read_only
    dset.metadata.read_only = True
    assert not dset.read_only
    assert dset.metadata.read_only
    dset[:] = 1
    with pytest.raises(ValueError, match="read-only"):
        _ = dset.add_metadata(some_more_info=1)


def test_copy() -> None:
    orig = Dataset(name="abcdefg", parent=None, read_only=True, shape=(10,), dtype=int, voltage=1.2, current=5.3)

    assert orig.read_only
    assert orig.name == "abcdefg"

    copy = orig.copy()
    assert isinstance(copy, Dataset)
    assert copy.read_only
    assert copy.metadata.read_only
    assert copy.name == "abcdefg"
    for i in range(10):
        assert orig[i] == copy[i]
    assert orig.metadata["voltage"] == copy.metadata["voltage"]
    assert orig.metadata["current"] == copy.metadata["current"]

    copy.read_only = False

    assert not copy.read_only
    assert not copy.metadata.read_only
    assert orig.read_only  # type: ignore[unreachable]
    assert orig.metadata.read_only

    val = 7 if orig[1] != 7 else 8
    copy[1] = val
    assert copy[1] == val
    assert orig[1] != copy[1]


def test_string_representation() -> None:
    dset = Dataset(name="abcd", parent=None, data=[[1, 2], [3, 4]], read_only=True, foo="bar")

    assert repr(dset) in [
        "<Dataset 'abcd' shape=(2, 2) dtype='<f8' (1 metadata)>",
        "<Dataset 'abcd' shape=(2L, 2L) dtype='<f8' (1 metadata)>",
    ]

    assert str(dset) == ("array([[1., 2.],\n       [3., 4.]])")

    assert str(dset.metadata) == "<Metadata 'abcd' {'foo': 'bar'}>"

    # just for fun, test more index access
    assert dset[0, 0] + dset[0, 1] == 3
    assert all(dset[:, 0] + dset[:, 1] == [3, 7])
    assert all(dset[0, :] + dset[1, :] == [4, 6])


def test_ndarray_attribute() -> None:
    dset = Dataset(name="abcd", parent=None, data=[[1, 2], [3, 4]], read_only=True)

    as_list = dset.tolist()
    assert isinstance(as_list, list)
    assert dset.tolist() == [[1, 2], [3, 4]]
    assert dset.flatten().tolist() == [1, 2, 3, 4]

    assert dset.max() == 4
    assert dset.min() == 1
    assert all(dset.max(axis=1) == [2, 4])
    assert all(dset.max(axis=0) == [3, 4])


def test_scalar() -> None:
    dset = Dataset(name="abcd", parent=None, data=5, read_only=True)
    assert len(dset) == 1
    assert dset.shape == ()
    assert dset.size == 1
    assert dset.data == 5.0


def test_add() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 + rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([5.0, 7.0, 9.0]))

    for lhs in ([4, 5, 6], d2):
        result = lhs + d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([5.0, 7.0, 9.0]))


def test_sub() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 - rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([-3.0, -3.0, -3.0]))

    for lhs in ([4, 5, 6], d2):
        result = lhs - d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([3.0, 3.0, 3.0]))


def test_mul() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    for rhs in ([4, 5, 6], d2):
        result = d1 * rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([4.0, 10.0, 18.0]))

    for lhs in ([4, 5, 6], d2):
        result = lhs * d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([4.0, 10.0, 18.0]))


def test_truediv() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 1])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 4, 10])

    for rhs in ([4.0, 4.0, 10.0], d2):
        result = d1 / rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0.25, 0.5, 0.1]))

    for lhs in ([4.0, 4.0, 10.0], d2):
        result = lhs / d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([4.0, 2.0, 10.0]))


def test_floordiv() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1e3, 1e4, 1e5])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[1e2, 1e3, 1e4])

    for rhs in ([1e2, 1e3, 1e4], d2):
        result = d1 // rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([10.0, 10.0, 10.0]))

    for lhs in ([1e2, 1e3, 1e4], d2):
        result = lhs // d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0.0, 0.0, 0.0]))


def test_pow() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    result = d1**3
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([1.0, 8.0, 27.0]))

    result = pow(d1, 3)
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([1.0, 8.0, 27.0]))

    result = 3**d1
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([3.0, 9.0, 27.0]))

    result = pow(3, d1)
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([3.0, 9.0, 27.0]))

    for rhs in ([4.0, 5.0, 6.0], d2):
        result = d1**rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([1.0, 32.0, 729.0]))

        result = pow(d1, rhs)
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([1.0, 32.0, 729.0]))

    for lhs in (np.array([4.0, 5.0, 6.0]), d2):
        result = lhs**d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([4.0, 25.0, 216.0]))

        result = pow(lhs, d1)  # pyright: ignore[reportCallIssue, reportArgumentType, reportUnknownVariableType]
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([4.0, 25.0, 216.0]))


def test_matmul() -> None:
    d1 = Dataset(name="d1", parent=None, read_only=True, data=[[1, 2], [3, 4]])
    d2 = Dataset(name="d2", parent=None, read_only=True, data=[[5, 6], [7, 8]])

    for rhs in ([[5, 6], [7, 8]], d2):
        result = np.matmul(d1, rhs)
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([[19, 22], [43, 50]]))

        result = d1 @ rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([[19, 22], [43, 50]]))

    for lhs in ([[5, 6], [7, 8]], d2):
        result = np.matmul(lhs, d1)
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([[23, 34], [31, 46]]))

        result = lhs @ d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([[23, 34], [31, 46]]))


def test_mod() -> None:
    d = Dataset(name="/d", parent=None, read_only=True, data=list(range(7)))

    result = d % 5
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([0, 1, 2, 3, 4, 0, 1]))

    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[4, 7])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[2, 3])

    for rhs in ([2, 3], d2):
        result = d1 % rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0, 1]))

    for lhs in ([2, 3], d2):
        result = lhs % d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([2, 3]))


def test_divmod() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[3, 7, 12, 52, 62])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.arange(1, 6))

    for rhs in ([1, 2, 3, 4, 5], d2):
        div, mod = divmod(d1, rhs)
        assert isinstance(div, Dataset)
        assert np.array_equal(div, np.array([3, 3, 4, 13, 12]))
        assert isinstance(mod, Dataset)
        assert np.array_equal(mod, np.array([0, 1, 0, 0, 2]))

    for lhs in ([1, 2, 3, 4, 5], d2):
        div, mod = divmod(lhs, d1)
        assert isinstance(div, Dataset)
        assert np.array_equal(div, np.array([0, 0, 0, 0, 0]))
        assert isinstance(mod, Dataset)
        assert np.array_equal(mod, np.array([1, 2, 3, 4, 5]))

    d = Dataset(name="/d", parent=None, read_only=True, data=np.arange(5))
    div, mod = divmod(d, 3)
    assert isinstance(div, Dataset)
    assert np.array_equal(div, np.array([0, 0, 0, 1, 1]))
    assert isinstance(mod, Dataset)
    assert np.array_equal(mod, np.array([0, 1, 2, 0, 1]))


def test_lshift() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=np.array([1, 2, 3, 4, 5]))
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.array([3, 7, 11, 15, 19]))

    result = d1 << 1
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([2, 4, 6, 8, 10]))

    result = 1 << d1
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([2, 4, 8, 16, 32]))

    for rhs in ([3, 7, 11, 15, 19], d2):
        result = d1 << rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([8, 256, 6144, 131072, 2621440]))

    for lhs in ([3, 7, 11, 15, 19], d2):
        result = lhs << d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([6, 28, 88, 240, 608]))


def test_rshift() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=np.array([1, 2, 3, 4, 5]))
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.array([3, 7, 12, 52, 62]))

    result = d1 >> 10
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([0, 0, 0, 0, 0]))

    result = 10 >> d1
    assert isinstance(result, Dataset)
    assert np.array_equal(result, np.array([5, 2, 1, 0, 0]))

    for rhs in ([3, 7, 12, 52, 62], d2):
        result = d1 >> rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0, 0, 0, 0, 0]))

    for lhs in ([3, 7, 12, 52, 62], d2):
        result = lhs >> d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([1, 1, 1, 3, 1]))


def test_and() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 & rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0, 1, 0, 1, 4, 5, 0, 1, 0]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs & d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([0, 1, 0, 1, 4, 5, 0, 1, 0]))


def test_xor() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 ^ rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([10, 10, 14, 14, 10, 10, 22, 22, 26]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs ^ d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([10, 10, 14, 14, 10, 10, 22, 22, 26]))


def test_or() -> None:
    d1 = Dataset(name="/d1", parent=None, read_only=True, data=np.arange(9))
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=np.arange(10, 19))

    for rhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = d1 | rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([10, 11, 14, 15, 14, 15, 22, 23, 26]))

    for lhs in ([10, 11, 12, 13, 14, 15, 16, 17, 18], d2):
        result = lhs | d1
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([10, 11, 14, 15, 14, 15, 22, 23, 26]))


def test_neg() -> None:
    # unary "-"

    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    for rhs in [[4, 5, 6], d2]:
        result = -d1 + rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([3, 3, 3]))


def test_pos() -> None:
    # unary "+"

    d1 = Dataset(name="/d1", parent=None, read_only=True, data=[1, 2, 3])
    d2 = Dataset(name="/d2", parent=None, read_only=True, data=[4, 5, 6])

    for rhs in [[4, 5, 6], d2]:
        result = +d1 - rhs
        assert isinstance(result, Dataset)
        assert np.array_equal(result, np.array([-3, -3, -3]))


def test_abs() -> None:
    d = Dataset(name="/d", parent=None, read_only=True, data=[1, -2, 3, -4])
    result = abs(d)
    assert isinstance(result, Dataset)
    assert result.name == "absolute(/d)"
    assert np.array_equal(result, np.array([1, 2, 3, 4]))


def test_invert() -> None:
    # unary "~"

    d = Dataset(name="/d", parent=None, read_only=True, data=np.array([1, -2, 3, -4]))

    result = ~d
    assert isinstance(result, Dataset)
    assert result.name == "invert(/d)"
    assert np.array_equal(result, np.array([-2, 1, -4, 3]))


def test_assignments() -> None:  # noqa: PLR0915
    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]), fruit="apple")
    d += 1
    assert isinstance(d, Dataset)
    assert d.name == "add(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="add(/d)", fruit="apple")
    assert np.array_equal(d, np.array([2, 3, 4]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]))
    d -= 1
    assert isinstance(d, Dataset)
    assert d.name == "subtract(/d)"
    assert d.parent is None
    assert len(d.metadata) == 0
    assert d.metadata == Metadata(read_only=True, node_name="subtract(/d)")
    assert np.array_equal(d, np.array([0, 1, 2]))

    d = Dataset(name="d", parent=None, read_only=False, data=np.array([1, 2, 3]), one=1)
    d *= 10
    assert isinstance(d, Dataset)
    assert d.name == "multiply(d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="multiply(d)", one=1)
    assert np.array_equal(d, np.array([10, 20, 30]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([10.0, 20.0, 30.0]), neg_one=-1)
    d /= 10
    assert isinstance(d, Dataset)
    assert d.name == "divide(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="divide(/d)", neg_one=-1)
    assert np.array_equal(d, np.array([1.0, 2.0, 3.0]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([10, 20, 30]))
    d //= 5
    assert isinstance(d, Dataset)
    assert d.name == "floor_divide(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="floor_divide(/d)")
    assert np.array_equal(d, np.array([2, 4, 6]))

    d = Dataset(name="dset", parent=None, read_only=False, data=np.array([10, 20, 30]), hello="world")
    d %= 15
    assert isinstance(d, Dataset)
    assert d.name == "remainder(dset)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="remainder(dset)", hello="world")
    assert np.array_equal(d, np.array([10, 5, 0]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]))
    d **= 3
    assert isinstance(d, Dataset)
    assert d.name == "power(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="power(/d)")
    assert np.array_equal(d, np.array([1, 8, 27]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]))
    d <<= 3
    assert isinstance(d, Dataset)
    assert d.name == "left_shift(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="left_shift(/d)")
    assert np.array_equal(d, np.array([8, 16, 24]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([10, 20, 30]))
    d >>= 2
    assert isinstance(d, Dataset)
    assert d.name == "right_shift(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="right_shift(/d)")
    assert np.array_equal(d, np.array([2, 5, 7]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]), one=1)
    d &= 2
    assert isinstance(d, Dataset)
    assert d.name == "bitwise_and(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="bitwise_and(/d)", one=1)
    assert np.array_equal(d, np.array([0, 2, 2]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]), apple="red")
    d ^= 2
    assert isinstance(d, Dataset)
    assert d.name == "bitwise_xor(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="bitwise_xor(/d)", apple="red")
    assert np.array_equal(d, np.array([3, 0, 1]))

    d = Dataset(name="/d", parent=None, read_only=False, data=np.array([1, 2, 3]), hi="hey")
    d |= 2
    assert isinstance(d, Dataset)
    assert d.name == "bitwise_or(/d)"
    assert d.parent is None
    assert d.metadata == Metadata(read_only=True, node_name="bitwise_or(/d)", hi="hey")
    assert np.array_equal(d, np.array([3, 2, 3]))


def test_numpy_function() -> None:
    # np.xxx() is also valid syntax with a Dataset

    array = np.array([1.0, 2.0, 3.0])
    d1 = Dataset(name="d1", parent=None, read_only=True, data=[1.0, 2.0, 3.0], one=1)

    cos = np.cos(d1)
    assert isinstance(cos, Dataset)  # type: ignore[unreachable]
    assert cos.name == "cos(d1)"  # type: ignore[unreachable]
    assert cos.parent is None
    assert cos.metadata == Metadata(read_only=False, node_name="cos(d1)", one=1)
    assert np.array_equal(cos, np.cos(array))

    sqrt = np.sqrt(d1)
    assert isinstance(sqrt, Dataset)
    assert sqrt.name == "sqrt(d1)"
    assert sqrt.parent is None
    assert sqrt.metadata == Metadata(read_only=False, node_name="sqrt(d1)", one=1)
    assert np.array_equal(sqrt, np.sqrt(array))

    _abs = np.abs(d1)
    assert isinstance(_abs, Dataset)
    assert _abs.name == "absolute(d1)"
    assert _abs.parent is None
    assert _abs.metadata == Metadata(read_only=False, node_name="absolute(d1)", one=1)
    assert np.array_equal(_abs, np.abs(array))

    _max = np.max(d1)
    assert isinstance(_max, float)
    assert _max == np.max(array)


def test_name_metadata_merged() -> None:
    a = Dataset(name="/a", parent=None, read_only=False, data=[1, 2, 3], fruit="apple")
    b = Dataset(name="b", parent=None, read_only=True, data=[4, 5, 6], one=1)
    c = Dataset(name="/c", parent=None, read_only=True, data=[7, 8, 9], hello="world", eat="cake")

    a += 1
    assert repr(a) == "<Dataset 'add(/a)' shape=(3,) dtype='<f8' (1 metadata)>"
    assert a.metadata == Metadata(read_only=False, node_name="add(/a)", fruit="apple")
    assert np.array_equal(a, [2, 3, 4])

    ba = b - a
    assert repr(ba) == "<Dataset 'subtract(b,add(/a))' shape=(3,) dtype='<f8' (2 metadata)>"
    assert ba.metadata == Metadata(read_only=False, node_name="subtract(b,add(/a))", fruit="apple", one=1)
    assert np.array_equal(ba, [2, 2, 2])

    d = np.sqrt(c + b - a)
    assert repr(d) == "<Dataset 'sqrt(subtract(add(/c,b),add(/a)))' shape=(3,) dtype='<f8' (4 metadata)>"
    assert d.metadata == Metadata(
        read_only=False, node_name="sqrt(subtract(add(/c,b),add(/a)))", fruit="apple", one=1, hello="world", eat="cake"
    )
    assert np.array_equal(d, np.sqrt([7 + 4 - 2, 8 + 5 - 3, 9 + 6 - 4]))


def test_invalid_name() -> None:
    d = Dataset(name="this is ok", parent=None, read_only=True)
    assert d.read_only
    assert d.name == "this is ok"

    # the name must be a non-empty string
    with pytest.raises(ValueError, match="cannot be an empty string"):
        _ = Dataset(name="", parent=None, read_only=True)

    # the name can contain a '/' if the parent is None
    d = Dataset(name="/a", parent=None, read_only=True)
    assert d.name == "/a"

    # the name cannot contain a '/' if the parent is not None
    for n in ["/", "/a", "a/b", "ab/"]:
        with pytest.raises(ValueError, match="cannot contain the '/' character"):
            _ = Dataset(name=n, parent=Root(""), read_only=True)

    # check that the name is forced to be unique if the parent is not None
    root = Root("")
    _ = root.create_group("msl")
    with pytest.raises(ValueError, match="is not unique"):
        _ = Dataset(name="msl", parent=root, read_only=True)


def test_eq() -> None:
    d = Dataset(name="a", parent=None, read_only=True, data=[1, 2, 3], one=1)
    assert d != [1, 2, 3]
    assert d is not None
    assert d != 8
    assert d == Dataset(name="a", parent=None, read_only=True, data=[1, 2, 3], one=1)
    assert d != Dataset(name="/a", parent=None, read_only=True, data=[1, 2, 3], one=1)  # names not equal
    assert d != Dataset(name="a", parent=None, read_only=True, data=[1, 2, 3], two=2)  # metadata not equal
    assert d != Dataset(name="a", parent=None, read_only=True, data=[-1, -2, -3], one=1)  # arrays not equal
