import logging
import types

import pytest

from msl.io import Dataset, DatasetLogging, Group, Root
from msl.io.metadata import Metadata


def test_instantiation() -> None:
    root = Root("some.file")
    assert root.name == "/"
    assert not root.read_only
    assert not root.metadata.read_only
    assert len(root) == 0
    assert len(root.metadata) == 0
    assert str(root).startswith("<Root")

    root = Root("C:\\path\\to\\a\\windows.file")
    assert root.name == "/"

    root = Root(r"\\network\drive with multiple\spa ces.file")
    assert root.name == "/"

    root = Root("/home/another.xxx")
    assert root.name == "/"
    assert not root.read_only
    assert not root.metadata.read_only
    assert len(root) == 0
    assert len(root.metadata) == 0

    root = Root("/home/another.xxx", one=1, two=2, three=3)
    assert root.name == "/"
    assert not root.read_only
    assert not root.metadata.read_only
    assert len(root) == 0
    assert root.metadata == Metadata(read_only=False, node_name="/", one=1, two=2, three=3)

    root.read_only = True

    # cannot add metadata
    with pytest.raises(ValueError, match=r"read-only"):
        root.add_metadata(four=4, five=5)

    root.read_only = False
    root.add_metadata(four=4, five=5)
    assert root.metadata == Metadata(read_only=False, node_name="/", one=1, two=2, three=3, four=4, five=5)


def test_create_group() -> None:
    root = Root("")

    # must specify a name for the group
    with pytest.raises(TypeError):
        root.create_group(read_only=True)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]

    assert not root.read_only
    assert not root.metadata.read_only

    root.read_only = True

    # cannot create a group since root is in read-only mode
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.create_group("xxx")

    root.read_only = False
    assert not root.read_only
    assert not root.metadata.read_only

    a = root.create_group("a")
    assert root.is_group(a)
    assert a.is_group(a)
    assert isinstance(a, Group)
    assert not a.read_only  # gets read-only value from root
    assert not a.metadata.read_only  # gets read-only value from root
    assert a.name == "/a"
    assert a.parent is root
    assert "a" in root

    # set read_only=True to create a subgroup that is read only but root is not read only
    b = root.create_group("b", read_only=True)
    assert b.read_only
    assert b.metadata.read_only
    assert not root.read_only
    assert not root.metadata.read_only
    assert b.name == "/b"
    assert b.parent is root
    assert "b" in root

    # cannot set the parent because this kwarg is pop'd
    c = root.create_group("c", parent=None)
    assert c.name == "/c"
    assert c.parent is root
    assert "c" in root
    assert len(c.metadata) == 0

    # create a subgroup with some metadata
    d = root.create_group("d", parent=None, one=1, two=2, three=3)
    assert d.name == "/d"
    assert d.parent is root
    assert "d" in root
    assert "parent" not in d.metadata
    assert d.metadata == Metadata(read_only=False, node_name="/d", one=1, two=2, three=3)

    # check that we can make root read only again
    root.read_only = True
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.create_group("xxx")

    # check that the subgroups of root make sense
    assert len(root) == 4
    assert "a" in root
    assert "b" in root
    assert "c" in root
    assert "d" in root
    assert "xxx" not in root


def test_create_dataset() -> None:  # noqa: PLR0915
    root = Root("")

    # must specify a name for the dataset
    with pytest.raises(TypeError):
        root.create_dataset()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]

    assert not root.read_only
    assert not root.metadata.read_only

    root.read_only = True

    # cannot create a dataset if root is in read-only mode
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.create_dataset("xxx")

    root.read_only = False
    assert not root.read_only
    assert not root.metadata.read_only

    # create an empty dataset (no data, no metadata)
    d1 = root.create_dataset("data1")
    assert root.is_dataset(d1)
    assert isinstance(d1, Dataset)
    assert not d1.read_only  # gets read-only value from root
    assert d1.name == "/data1"
    assert d1.parent is root
    assert d1.size == 0
    assert d1.dtype == float
    assert len(d1.metadata) == 0
    assert "data1" in root

    # create a dataset with shape and metadata
    d2 = root.create_dataset("data2", shape=(10, 5), one=1)
    assert d2.name == "/data2"
    assert d2.parent is root
    assert d2.shape == (10, 5)
    assert d2.size == 50
    assert d2.dtype == float
    assert len(d2.metadata) == 1
    assert d2.metadata == Metadata(read_only=False, node_name="/data2", one=1)
    assert "data2" in root

    # cannot set the parent because this kwarg is pop'd
    d3 = root.create_dataset("data3", parent=None)
    assert d3.name == "/data3"
    assert d3.parent is root
    assert "data3" in root

    # creating a dataset in read-only mode doesn't change root's read mode
    d4 = root.create_dataset("data4", read_only=True)
    assert d4.read_only
    assert d4.metadata.read_only
    assert not root.read_only
    assert not root.metadata.read_only
    assert "data4" in root

    # check kwargs
    d5 = root.create_dataset("data5", parent=None, read_only=True, order="F", one=1, two=2, three=3)
    assert d5.name == "/data5"
    assert d5.parent is root
    assert d5.read_only
    assert d5.metadata.read_only
    assert not root.read_only
    assert not root.metadata.read_only
    assert "data5" in root
    assert "order" not in d5.metadata
    assert d5.metadata == Metadata(read_only=False, node_name="/data5", one=1, two=2, three=3)

    # check that we can make root read only again
    root.read_only = True
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.create_dataset("xxx")

    # check that the datasets of root make sense
    assert len(root) == 5
    assert "data1" in root
    assert "data2" in root
    assert "data3" in root
    assert "data4" in root
    assert "data5" in root
    assert "xxx" not in root


def test_accessing_subgroups_sub_datasets() -> None:  # noqa: PLR0915
    root = Root("")

    a = root.create_group("a")
    d1 = a.create_dataset("d1")
    b = a.create_group("b")
    c = b.create_group("c")
    d = c.create_group("d")
    d2 = d.create_dataset("d2")
    d3 = d.create_dataset("d3")

    assert a is root["/a"]
    assert d1 is root["/a/d1"]
    assert b is root["/a/b"]
    assert c is root["/a/b/c"]
    assert d is root["/a/b/c/d"]
    assert d2 is root["/a/b/c/d/d2"]
    assert d3 is root["/a/b/c/d/d3"]

    assert d1 is a["/d1"]
    assert b is a["/b"]
    assert c is a["/b/c"]
    assert d is a["/b/c/d"]
    assert d2 is a["/b/c/d/d2"]
    assert d3 is a["/b/c/d/d3"]

    assert c is b["/c"]
    assert d is b["/c/d"]
    assert d2 is b["/c/d/d2"]
    assert d3 is b["/c/d/d3"]

    assert d is c["/d"]
    assert d2 is c["/d/d2"]
    assert d3 is c["/d/d3"]

    assert d2 is d["/d2"]
    assert d3 is d["/d3"]

    assert root.a is root["a"]
    assert root.a.d1 is root["a"]["d1"]
    assert root.a.b is root["a"]["b"]
    assert root.a.b.c is root["a"]["b"]["c"]
    assert root.a.b.c.d is root["a"]["b"]["c"]["d"]
    assert root.a.b.c.d.d2 is root["a"]["b"]["c"]["d"]["d2"]
    assert root.a.b.c.d.d3 is root["a"]["b"]["c"]["d"]["d3"]

    assert root["a"].b["c"].d is root["/a/b/c/d"]  # type: ignore[union-attr]  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    assert root.a.d1 is a["d1"]
    assert root.a.b is a["b"]
    assert root.a.b.c is b["c"]
    assert root.a.b.c.d is c["d"]
    assert root.a.b.c.d.d2 is d["d2"]

    aa = root.a
    assert aa.b is root.a.b
    assert aa.b is root["a"]["b"]

    cc = root.a.b.c
    assert cc.d is root.a.b.c.d
    assert cc["d"] is root["a"]["b"]["c"]["d"]

    with pytest.raises(KeyError):
        _ = root["xxx"]

    with pytest.raises(AttributeError):
        _ = root.xxx


def test_in_not_in() -> None:
    root = Root("")

    a = root.create_group("a")
    _ = a.create_dataset("first dataset")
    b = a.create_group("b")
    c = b.create_group("c")
    d = c.create_group("d")
    _ = d.create_dataset("second dataset")

    assert "xxx" not in root
    assert "/" not in root
    assert "a" in root
    assert "/a" in root
    assert "first dataset" in a
    assert "/a/first dataset" in root
    assert "first dataset" not in root
    assert "b" in a
    assert "/b" in a
    assert "/a/b" in root
    assert "c" in b
    assert "/c" in b
    assert "/a/b/c" in root
    assert "/c" not in a
    assert "d" in c
    assert "/d" in c
    assert "second dataset" in d
    assert "/a/b/c/d/second dataset" in root


def test_read_only_propagates() -> None:  # noqa: PLR0915
    root = Root("")

    g1 = root.create_group("g1")
    d1 = g1.create_dataset("d1")
    g2 = g1.create_group("g2")
    g3 = g2.create_group("g3")
    d3 = g3.create_dataset("d3")
    g4 = g3.create_group("g4")

    # all sub groups/datasets inherit roots read-only value
    assert not root.read_only
    assert not root.metadata.read_only
    assert not g1.read_only
    assert not g1.metadata.read_only
    assert not d1.read_only
    assert not d1.metadata.read_only
    assert not g2.read_only
    assert not g2.metadata.read_only
    assert not g3.read_only
    assert not g3.metadata.read_only
    assert not d3.read_only
    assert not d3.metadata.read_only
    assert not g4.read_only
    assert not g4.metadata.read_only

    # make all sub groups/datasets read only by only changing root
    root.read_only = True
    assert root.read_only
    assert root.metadata.read_only
    assert g1.read_only  # type: ignore[unreachable]
    assert g1.metadata.read_only
    assert d1.read_only
    assert d1.metadata.read_only
    assert g2.read_only
    assert g2.metadata.read_only
    assert g3.read_only
    assert g3.metadata.read_only
    assert d3.read_only
    assert d3.metadata.read_only
    assert g4.read_only
    assert g4.metadata.read_only

    # make all sub groups/datasets <= g2 writeable
    g2.read_only = False
    assert root.read_only
    assert root.metadata.read_only
    assert g1.read_only
    assert g1.metadata.read_only
    assert d1.read_only
    assert d1.metadata.read_only
    assert not g2.read_only
    assert not g2.metadata.read_only
    assert not g3.read_only
    assert not g3.metadata.read_only
    assert not d3.read_only
    assert not d3.metadata.read_only
    assert not g4.read_only
    assert not g4.metadata.read_only


def test_datasets_groups() -> None:
    root = Root("")

    d0 = root.create_dataset("d0")
    g1 = root.create_group("g1")
    d1 = g1.create_dataset("d1")
    g2 = g1.create_group("g2")
    g3 = g2.create_group("g3")
    d3 = g3.create_dataset("d3")
    g4 = g3.create_group("g4")

    # cannot create 2 sub-Groups with the same key
    with pytest.raises(ValueError, match=r"unique"):
        _ = root.create_group("g1")

    # cannot create 2 Datasets with the same key
    with pytest.raises(ValueError, match=r"unique"):
        _ = g3.create_group("d3")

    assert isinstance(root.datasets(), types.GeneratorType)
    datasets = list(root.datasets())
    assert len(datasets) == 3
    assert d0 in datasets
    assert d1 in datasets
    assert d3 in datasets

    assert isinstance(root.groups(), types.GeneratorType)
    groups = list(root.groups())
    assert len(groups) == 4
    assert g1 in groups
    assert g2 in groups
    assert g3 in groups
    assert g4 in groups

    root_items = {
        "/d0": d0,
        "/g1": g1,
        "/g1/d1": d1,
        "/g1/g2": g2,
        "/g1/g2/g3": g3,
        "/g1/g2/g3/d3": d3,
        "/g1/g2/g3/g4": g4,
    }
    for key, value in root.items():
        assert key in root_items
        assert value is root_items[key]
        del root_items[key]


def test_delete_vertex() -> None:  # noqa: PLR0915
    root = Root("")

    _ = root.create_group("g1")
    g2 = root.create_group("g2")
    _ = g2.create_group("a")
    _ = g2.create_dataset("b")
    c = g2.create_group("c")
    _ = root.create_group("g3")
    _ = c.create_dataset("cd1")
    _ = c.create_dataset("cd2")
    _ = c.create_group("cg3")

    with pytest.raises(KeyError):  # invalid key
        del root["x"]

    with pytest.raises(AttributeError):  # invalid attribute
        del root.x

    root.read_only = True

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root["g1"]

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root.g2

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root.g2.c.cd1  # pyright: ignore[reportAttributeAccessIssue]

    assert "/g1" in root
    assert "/g2" in root
    assert "/g2/a" in root
    assert "/g2/b" in root
    assert "/g2/c" in root
    assert "/g2/c/cd1" in root
    assert "/g2/c/cd2" in root
    assert "/g2/c/cg3" in root
    assert "/g3" in root

    root.read_only = False

    del root["g1"]
    assert "/g1" not in root
    assert "/g2" in root
    assert "/g2/a" in root
    assert "/g2/b" in root
    assert "/g2/c" in root
    assert "/g2/c/cd1" in root
    assert "/g2/c/cd2" in root
    assert "/g2/c/cg3" in root
    assert "/g3" in root

    root.read_only = True

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root["g2"]

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root.g2

    with pytest.raises(ValueError, match=r"read-only"):  # read-only mode
        del root.g2.c.cg3  # pyright: ignore[reportAttributeAccessIssue]

    root.read_only = False

    del root["/g2/a"]
    assert "/g2" in root
    assert "/g2/a" not in root
    assert "/g2/b" in root
    assert "/g2/c" in root
    assert "/g2/c/cd1" in root
    assert "/g2/c/cd2" in root
    assert "/g2/c/cg3" in root
    assert "/g3" in root

    del root["g2"]["c"]["cg3"]  # type: ignore[union-attr]  # pyright: ignore[reportIndexIssue]
    assert "/g2" in root
    assert "/g2/b" in root
    assert "/g2/c" in root
    assert "/g2/c/cd1" in root
    assert "/g2/c/cd2" in root
    assert "/g2/c/cg3" not in root
    assert "/g3" in root

    del root.g2.b  # pyright: ignore[reportAttributeAccessIssue]
    assert "/g2" in root
    assert "/g2/b" not in root
    assert "/g2/c" in root
    assert "/g2/c/cd1" in root
    assert "/g2/c/cd2" in root
    assert "/g3" in root

    del root["/g2"]
    assert "/g2" not in root
    assert "/g2/c" not in root
    assert "/g2/c/cd1" not in root
    assert "/g2/c/cd2" not in root
    assert "/g3" in root

    del root["g3"]
    assert len(root) == 0


def test_auto_create_subgroups() -> None:
    root = Root("")

    assert len(list(root.groups())) == 0
    assert len(list(root.datasets())) == 0

    _ = root.create_group("a/group2/c/group4/d/group6")
    _ = root.create_dataset("/w/x/y/z", shape=(10,))

    # intermediate Groups get created automatically
    with pytest.raises(ValueError, match=r"unique"):
        _ = root.create_group("a/group2/c")
    with pytest.raises(ValueError, match=r"unique"):
        _ = root.create_group("/w/x")

    assert len(list(root.groups())) == 9

    _ = root.a.group2.c.group4.create_group("/m/n")

    assert len(list(root.groups())) == 11

    assert "a" in root
    assert "group2" in root.a
    assert "c" in root.a.group2
    assert "group4" in root.a.group2.c
    assert "m" in root.a.group2.c.group4
    assert "m/n" in root.a.group2.c.group4
    assert "n" in root.a.group2.c.group4.m
    assert "d" in root.a.group2.c.group4
    assert "group6" in root.a.group2.c.group4.d

    assert "w" in root
    assert "w/x" in root
    assert "w/x/y" in root
    assert "w/x/y/z" in root
    assert root.is_dataset(root["/w/x/y/z"])
    assert root["/w/x/y/z"].shape == (10,)


def test_requires() -> None:  # noqa: PLR0915
    root = Root("")

    #
    # Groups
    #
    assert "a" not in root

    a = root.require_group("a")
    assert root.is_group(a)
    assert "a" in root
    assert "/a" in root
    assert root.require_group("a") is a
    assert root.require_group("/a") is a

    # group exists but adding new metadata to it
    a2 = root.require_group("a", one=1)
    assert a2 is a
    assert a.metadata.one == 1
    assert a2.metadata.one == 1

    # try to add Metadata to a Group that is read only
    root.read_only = True
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.require_group("a", two=2)
    # read-only mode
    with pytest.raises(ValueError, match=r"read-only"):
        _ = a.create_group("b")

    root.read_only = False
    b = a.create_group("b")
    with pytest.raises(ValueError, match=r"unique"):
        _ = a.create_group("b")
    assert root.require_group("a/b") is b

    _ = root.require_group("/a/b/c/d/e/", foo="bar")
    assert "a" in root
    assert "b" in a
    assert "c" in root.a.b
    assert "d" in root.a.b.c
    assert "foo" not in root.metadata
    assert "foo" not in root.a.metadata
    assert "foo" not in root.a.b.metadata
    assert "foo" not in root.a.b.c.metadata
    assert "foo" not in root.a.b.c.d.metadata
    assert "foo" in root.a.b.c.d.e.metadata
    assert root.a.b.c.d.e.metadata.foo == "bar"

    # make sure that calling require_group from a sub-Group works properly
    c = a.b.c
    d = c.d
    e = d.e
    assert a.require_group("b") is b
    assert a.require_group("/b/c") is c
    assert a.require_group("b/c/") is root.a.b.c
    assert b.require_group("c/d/e") is e
    assert b.require_group("c/d/e") is root.a.b.c.d.e
    assert c.require_group("d") is d
    assert c.require_group("d") is root.a.b.c.d
    assert c.require_group("d/e") is e
    assert c.require_group("/d/e/") is root.a.b.c.d.e
    assert d.require_group("e") is e
    assert d.require_group("e/") is root.a.b.c.d.e

    # change the read-only value of the new sub-groups that are required
    assert not root.read_only
    bb = root.require_group("aa/bb", read_only=True, hello="world")
    assert bb is root.aa.bb
    assert not root.read_only
    assert not root.metadata.read_only
    assert root.aa.read_only
    assert root.aa.metadata.read_only
    assert bb.read_only
    assert bb.metadata.read_only
    assert len(root.aa.bb.metadata) == 1
    assert root.aa.bb.metadata.hello == "world"
    with pytest.raises(ValueError, match=r"read-only"):
        bb.add_metadata(one=1)
    bb.read_only = False
    bb.add_metadata(one=1)
    assert len(root.aa.bb.metadata) == 2
    assert root.aa.bb.metadata.hello == "world"
    assert root.aa.bb.metadata.one == 1
    assert root.aa.read_only
    assert root.aa.metadata.read_only
    with pytest.raises(ValueError, match=r"read-only"):
        root.aa.add_metadata(two=2)

    # require root.aa.bb but change the read-only value
    assert not root.aa.bb.read_only
    bb2 = root.require_group("aa/bb", read_only=True)
    assert bb2 is root.aa.bb
    assert bb2.read_only
    assert root.aa.bb.read_only
    with pytest.raises(ValueError, match=r"read-only"):
        bb2.add_metadata(three=3)

    #
    # Datasets
    #
    with pytest.raises(ValueError, match=r"unique"):
        _ = root.require_dataset("a")  # 'a' is already a Group but we are creating a Dataset
    w = root.require_dataset("w")
    assert root.is_dataset(w)
    assert "w" in root
    assert "/w" in root
    assert root.require_dataset("w") is w
    assert root.require_dataset("/w/") is w

    # dataset exists but adding new metadata to it
    w2 = root.require_dataset("w", one=1)
    assert w2 is w
    assert len(w2.metadata) == 1
    assert w.metadata.one == 1
    assert w2.metadata.one == 1

    # dataset exists but ignores key-value pairs that are not Metadata but are used to create the dataset
    w2 = root.require_dataset("w", shape=(10,), order=None)
    assert w2 is w
    assert len(w2.metadata) == 1
    assert w.metadata.one == 1
    assert w2.metadata.one == 1
    assert "shape" not in w2.metadata
    assert "order" not in w2.metadata

    # try to add Metadata to a Dataset that is read only
    root.read_only = True
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.require_dataset("w", two=2)
    # read-only mode
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.create_dataset("x")

    # add a Dataset to the 'a' Group
    root.read_only = False
    x = a.create_dataset("x")
    with pytest.raises(ValueError, match=r"unique"):
        _ = a.create_dataset("x")
    assert root.require_dataset("/a/x") is x

    # add a Dataset to the 'b' Group, create the necessary sub-Groups automatically
    _ = root.require_dataset("/b/x/y/z", data=[1, 2, 3, 4], foo="bar")
    assert root.is_group(root.b)
    assert root.is_group(root.b.x)
    assert root.is_group(root.b.x.y)
    assert root.is_dataset(root.b.x.y.z)
    assert "w" in root
    assert "b" in root
    assert "x" in root.b
    assert "y" in root.b.x
    assert "z" in root.b.x.y
    assert "foo" not in root.metadata
    assert "foo" not in root.b.metadata
    assert "foo" not in root.b.x.metadata
    assert "foo" not in root.b.x.y.metadata
    assert "foo" in root.b.x.y.z.metadata
    assert root.b.x.y.z.metadata.foo == "bar"
    assert root.b.x.y.z.shape == (4,)
    assert isinstance(root.b.x.y.z, Dataset)
    assert root.b.x.y.z.tolist() == [1, 2, 3, 4]
    assert root.b.x.y.z.max() == 4

    # change the read-only value of the new Dataset that is required
    assert not root.read_only
    yy = root.require_dataset("xx/yy", read_only=True, hello="world")
    assert yy is root.xx.yy
    assert not root.read_only
    assert not root.metadata.read_only
    assert root.xx.read_only
    assert root.xx.metadata.read_only
    assert yy.read_only
    assert yy.metadata.read_only
    assert len(root.xx.yy.metadata) == 1
    assert root.xx.yy.metadata.hello == "world"
    with pytest.raises(ValueError, match=r"read-only"):
        yy.add_metadata(one=1)
    yy.read_only = False
    yy.add_metadata(one=1)
    assert len(root.xx.yy.metadata) == 2
    assert root.xx.yy.metadata.hello == "world"
    assert root.xx.yy.metadata.one == 1
    assert root.xx.read_only
    assert root.xx.metadata.read_only
    with pytest.raises(ValueError, match=r"read-only"):
        root.xx.add_metadata(two=2)

    # require root.xx.yy but change the read-only value
    assert not root.xx.yy.read_only
    yy2 = root.require_dataset("/xx/yy/", read_only=True)
    assert yy2 is root.xx.yy
    assert yy2.read_only
    assert root.xx.yy.read_only
    with pytest.raises(ValueError, match=r"read-only"):
        yy2.add_metadata(three=3)

    # make sure that calling require_dataset from a sub-Group works properly
    assert isinstance(root.a, Group)
    a = root.a
    assert a.require_dataset("x") is x
    assert a.require_dataset("/x") is root.a.x
    assert isinstance(root["b"], Group)
    b = root["b"]
    assert b.require_dataset("x/y/z") is root.b.x.y.z
    x = root["b"]["x"]  # type: ignore[assignment]
    assert x.require_dataset("/y/z") is root.b.x.y.z  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
    y = root["b"]["x"]["y"]
    assert y.require_dataset("/z/") is root.b.x.y.z  # type: ignore[union-attr]  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
    assert root["b"]["x"]["y"].require_dataset("z") is root.b.x.y.z  # type: ignore[union-attr]  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
    xx = root.xx
    assert xx.require_dataset("yy") is root["xx"]["yy"]
    assert root.xx.require_dataset("yy/") is yy2


def test_tree() -> None:
    root = Root("")
    a = root.create_group("a")
    _ = a.create_dataset("d1")
    b = a.create_group("b")
    _ = b.create_dataset("d2")
    c = b.create_group("c")
    _ = root.create_group("x/y/z")
    d = c.create_group("d")
    _ = a.create_dataset("d3")
    _ = root.create_dataset("d4")
    _ = d.create_dataset("d5")
    _ = d.create_dataset("d6")
    _ = root.create_dataset("d7")

    tree = """
<Root '' (7 groups, 7 datasets, 0 metadata)>
  <Group '/a' (3 groups, 5 datasets, 0 metadata)>
    <Group '/a/b' (2 groups, 3 datasets, 0 metadata)>
      <Group '/a/b/c' (1 group, 2 datasets, 0 metadata)>
        <Group '/a/b/c/d' (0 groups, 2 datasets, 0 metadata)>
          <Dataset '/a/b/c/d/d5' shape=(0,) dtype='<f8' (0 metadata)>
          <Dataset '/a/b/c/d/d6' shape=(0,) dtype='<f8' (0 metadata)>
      <Dataset '/a/b/d2' shape=(0,) dtype='<f8' (0 metadata)>
    <Dataset '/a/d1' shape=(0,) dtype='<f8' (0 metadata)>
    <Dataset '/a/d3' shape=(0,) dtype='<f8' (0 metadata)>
  <Dataset '/d4' shape=(0,) dtype='<f8' (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype='<f8' (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 group, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    assert root.tree() == tree[1:]  # skip the first line

    # use del instead of Group.remove()
    del root.a.b.c  # pyright: ignore[reportAttributeAccessIssue]

    tree = """
<Root '' (5 groups, 5 datasets, 0 metadata)>
  <Group '/a' (1 group, 3 datasets, 0 metadata)>
    <Group '/a/b' (0 groups, 1 dataset, 0 metadata)>
      <Dataset '/a/b/d2' shape=(0,) dtype='<f8' (0 metadata)>
    <Dataset '/a/d1' shape=(0,) dtype='<f8' (0 metadata)>
    <Dataset '/a/d3' shape=(0,) dtype='<f8' (0 metadata)>
  <Dataset '/d4' shape=(0,) dtype='<f8' (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype='<f8' (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 group, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    assert root.tree() == tree[1:]  # skip the first line

    # use Group.remove() instead of del
    assert root.remove("a") is a

    tree = """
<Root '' (3 groups, 2 datasets, 0 metadata)>
  <Dataset '/d4' shape=(0,) dtype='<f8' (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype='<f8' (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 group, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    assert root.tree() == tree[1:]  # skip the first line

    # increase the indentation
    tree = """
<Root '' (3 groups, 2 datasets, 0 metadata)>
     <Dataset '/d4' shape=(0,) dtype='<f8' (0 metadata)>
     <Dataset '/d7' shape=(0,) dtype='<f8' (0 metadata)>
     <Group '/x' (2 groups, 0 datasets, 0 metadata)>
          <Group '/x/y' (1 group, 0 datasets, 0 metadata)>
               <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    assert root.tree(indent=5) == tree[1:]  # skip the first line


def test_add_group() -> None:  # noqa: PLR0915
    root = Root("some file")

    for item in [{}, (), [], None, Dataset(name="dset", parent=None, read_only=False)]:  # type: ignore[var-annotated]  # pyright: ignore[reportUnknownVariableType]
        with pytest.raises(TypeError):
            root.add_group("name", item)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

    root2 = Root("New")
    assert len(root2) == 0

    #
    # add a Group that does not contain sub-Groups nor Datasets
    #

    # add to the Root Group
    root2.add_group("", root.create_group("a", one=1, foo="bar"))
    assert len(root2) == 1
    assert root2.a is not root.a
    assert "/a" in root2
    assert len(root2.a.metadata) == 2
    assert root2.a.metadata.one == 1
    assert root2.a.metadata["foo"] == "bar"

    root2.clear()  # also tests Root.clear()
    assert len(root2) == 0

    # creates an "/B" Group and then add to it
    root2.add_group("B", root.create_group("b", two=2))
    assert len(root2) == 2
    assert root2.B.b is not root.b
    assert "/B/b" in root2
    assert "B" in root2
    assert "b" in root2.B
    assert "/B/b" in root2
    assert len(root2.B.metadata) == 0
    assert len(root2.B.b.metadata) == 1
    assert root2.B.b.metadata.two == 2

    root2.clear()
    assert len(root2) == 0

    # creates an "/A/B/C" Group and then add to it (add a ridiculous amount of '/')
    root2.add_group("/////A/B/C//////////", root.create_group("c", x="x", y="y"))
    assert len(root2) == 4
    assert root2.A.B.C.c is not root.c
    assert "/A" in root2
    assert "A/B" in root2
    assert "/A/B/C" in root2
    assert "/A/B/C/c" in root2
    assert "/c" in root2.A.B.C
    assert len(root2.A.metadata) == 0
    assert len(root2.A.B.metadata) == 0
    assert len(root2.A.B.C.metadata) == 0
    assert len(root2.A.B.C.c.metadata) == 2
    assert root2.A.B.C.c.metadata.x == "x"
    assert root2["A"]["B"].C["c"].metadata["y"] == "y"  # type: ignore[union-attr]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]

    # verify root's tree
    assert len(root) == 3
    assert "a" in root
    assert "/b" in root
    assert "c" in root
    assert len(root.a.metadata) == 2
    assert root.a.metadata.one == 1
    assert root.a.metadata.foo == "bar"
    assert len(root.b.metadata) == 1
    assert root.b.metadata.two == 2
    assert len(root.c.metadata) == 2
    assert root.c.metadata.x == "x"
    assert root.c.metadata.y == "y"

    # add some Datasets to root
    _ = root.b.create_dataset("/x", data=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    _ = root.c.create_dataset("y/z", shape=(3, 4), meta="data")
    assert "x" in root.b
    assert "z" in root.c.y

    # add root to root2
    root2.add_group("/old", root)
    assert len(root2) == 11
    assert "/A" in root2
    assert "A/B" in root2
    assert "/A/B/C" in root2
    assert "/A/B/C/c" in root2
    assert "/c" in root2.A.B.C
    assert "old" in root2
    assert "old/a" in root2
    assert "/old/b" in root2
    assert "/old/c" in root2
    assert "/old/b/x" in root2
    assert "y" in root2.old.c
    assert "/y/z" in root2.old.c
    assert len(root2.A.metadata) == 0
    assert len(root2.A.B.metadata) == 0
    assert len(root2.A.B.C.metadata) == 0
    assert len(root2.A.B.C.c.metadata) == 2
    assert root2.A.B.C.c.metadata.x == "x"
    assert root2["A"]["B"].C["c"].metadata["y"] == "y"  # type: ignore[union-attr]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    assert len(root2.old.a.metadata) == 2
    assert root2.old.a.metadata.one == 1
    assert root2.old.a.metadata.foo == "bar"
    assert len(root2.old.b.metadata) == 1
    assert root2.old.b.metadata.two == 2
    assert len(root2.old.c.metadata) == 2
    assert root2.old.c.metadata.x == "x"
    assert root2.old.c.metadata.y == "y"
    assert len(root2.old.b.metadata) == 1
    assert root2.old.b.metadata.two == 2
    assert len(root2.old.c.metadata) == 2
    assert root2.old.c.metadata.x == "x"
    assert root2.old["c"].metadata["y"] == "y"  # type: ignore[union-attr]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    assert len(root2.old.c.y.metadata) == 0
    assert len(root2.old.c.y.z.metadata) == 1
    assert root2.old.c.y.z.metadata.meta == "data"
    assert root2.old.b.x.shape == (10,)
    assert root2.old.c.y.z.shape == (3, 4)

    # the Metadata is a copy
    root2.old.c.y.z.metadata.meta = "new value"
    assert root2.old.c.y.z.metadata.meta is not root.c.y.z.metadata.meta
    assert root2.old.c.y.z.metadata.meta == "new value"
    assert root.c.y.z.metadata.meta == "data"

    # the data in the Dataset is a copy
    assert root2.old.b.x.data is not root.b.x.data
    assert root2.old.c.y.z.data is not root.c.y.z.data
    assert isinstance(root2.old.b.x, Dataset)
    root2.old.b.x[:] = 1
    assert sum(root2.old.b.x) == 10
    assert isinstance(root.b.x, Dataset)
    assert sum(root.b.x.tolist()) == 0


def test_add_dataset() -> None:
    root = Root("some file")
    for item in [{}, (), [], None, 1.0, Root("r"), Group(name="group", parent=None, read_only=True)]:  # type: ignore[var-annotated]  # pyright: ignore[reportUnknownVariableType]
        with pytest.raises(TypeError):
            root.add_dataset("name", item)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

    assert len(root) == 0

    dset1 = Dataset(name="dset1", parent=None, read_only=False, data=[1, 2, 3], dtype=int)
    dset2 = Dataset(name="dset2", parent=None, read_only=False, data=[4.0, 5.0, 6.0], foo="bar")
    dset3 = Dataset(name="dset3", parent=None, read_only=False, data=[-23.4, 1.78], one=1, two=2)

    root.add_dataset("dset1_copy", dset1)

    d = root.create_group("a/b/c/d")
    c = d.parent
    assert c is root.a.b.c
    assert c is not None
    c.add_dataset("dset2_copy", dset2)

    c.add_dataset("/x/y/dset3_copy", dset3)

    assert len(list(root.datasets())) == 3
    assert len(list(root.a.datasets())) == 2
    assert len(list(root.a.b.datasets())) == 2
    assert len(list(root.a.b.c.datasets())) == 2
    assert len(list(root.a.b.c.x.datasets())) == 1
    assert len(list(root.a.b.c.x.y.datasets())) == 1
    assert len(list(root.a.b.c.d.datasets())) == 0

    assert root.dset1_copy is not dset1
    assert root.a.b.c.dset2_copy is not dset2
    assert root.a.b.c.x.y.dset3_copy is not dset3

    assert all(v1 == v2 for v1, v2 in zip(dset1, root.dset1_copy))
    assert all(v1 == v2 for v1, v2 in zip(dset2, root.a.b.c.dset2_copy))
    assert all(v1 == v2 for v1, v2 in zip(dset3, root.a.b.c.x.y.dset3_copy))

    assert len(root.dset1_copy.metadata) == 0
    assert len(c.dset2_copy.metadata) == 1
    assert c.dset2_copy.metadata.foo == "bar"
    assert len(c.x.y.dset3_copy.metadata) == 2
    assert c.x.y.dset3_copy.metadata["one"] == 1
    assert isinstance(c["x"]["y"]["dset3_copy"], Dataset)
    assert c["x"]["y"]["dset3_copy"].metadata.two == 2  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


def test_add_dataset_logging() -> None:  # noqa: PLR0915
    num_initial_handlers = len(logging.getLogger().handlers)

    logger = logging.getLogger("test_add_dataset_logging")

    root = Root("some file")
    for item in [  # type: ignore[var-annotated]  # pyright: ignore[reportUnknownVariableType]
        {},
        (),
        [],
        None,
        1.0,
        Root("r"),
        Group(name="group", parent=None, read_only=True),
        Dataset(name="d", parent=None, read_only=True),
    ]:
        with pytest.raises(TypeError):
            root.add_dataset_logging("name", item)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

    assert len(root) == 0
    assert len(logger.handlers) == 0
    assert len(logging.getLogger().handlers) == num_initial_handlers

    dset_log1 = root.create_dataset_logging(
        "dset_log1", level="DEBUG", attributes=["levelname", "message"], logger=logger, date_fmt="%H-%M"
    )

    logger.info("bang!")

    root2 = Root("some file")
    _ = root2.create_group("a/b/c")
    b = root2.a.b
    _ = b.add_dataset_logging("x/y/dset_log2", dset_log1)

    assert len(logger.handlers) == 2
    assert len(logging.getLogger().handlers) == num_initial_handlers

    logger.debug("hello")
    logger.info("world")

    dset_log1.remove_handler()
    assert len(logger.handlers) == 1
    assert len(logging.getLogger().handlers) == num_initial_handlers

    logger.warning("foo")
    logger.error("bar")

    assert dset_log1.metadata["logging_level"] == logging.DEBUG
    assert dset_log1.metadata.logging_level_name == "DEBUG"
    assert dset_log1.metadata.logging_date_format == "%H-%M"
    assert dset_log1.level == logging.DEBUG
    assert dset_log1.date_fmt == "%H-%M"
    assert dset_log1.logger is logger
    assert all(a == b for a, b in zip(dset_log1.attributes, ["levelname", "message"]))

    assert b.x.y.dset_log2.metadata["logging_level"] == logging.DEBUG
    assert b.x.y.dset_log2.metadata.logging_level_name == "DEBUG"
    assert b.x.y.dset_log2.metadata.logging_date_format == "%H-%M"
    assert b.x.y.dset_log2.level == logging.DEBUG
    assert b.x.y.dset_log2.date_fmt == "%H-%M"
    assert b.x.y.dset_log2.logger is logger
    assert all(a == b for a, b in zip(dset_log1.attributes, b.x.y.dset_log2.attributes))

    assert root.dset_log1.data.size == 3
    assert isinstance(root.dset_log1, DatasetLogging)
    row = root.dset_log1.data[0]
    assert row["levelname"] == "INFO"
    assert row["message"] == "bang!"
    row = root.dset_log1.data[1]
    assert row["levelname"] == "DEBUG"
    assert row["message"] == "hello"
    row = root.dset_log1.data[2]
    assert row["levelname"] == "INFO"
    assert row["message"] == "world"

    assert root2.a.b.x.y.dset_log2.data.size == 5
    y = b.x.y
    row = root.dset_log1[0]
    assert row["levelname"] == "INFO"
    assert row["message"] == "bang!"
    assert isinstance(y.dset_log2, DatasetLogging)
    row = y.dset_log2[1]
    assert row["levelname"] == "DEBUG"
    assert row["message"] == "hello"
    row = y.dset_log2[2]
    assert row["levelname"] == "INFO"
    assert row["message"] == "world"
    row = y.dset_log2[3]
    assert row["levelname"] == "WARNING"
    assert row["message"] == "foo"
    row = y.dset_log2[4]
    assert row["levelname"] == "ERROR"
    assert row["message"] == "bar"

    assert isinstance(root2.a.b.x.y.dset_log2, DatasetLogging)
    root2.a.b.x.y.dset_log2.remove_handler()

    assert len(logger.handlers) == 0
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_remove() -> None:  # noqa: PLR0915
    root = Root("")
    a = root.create_group("a")
    _ = a.create_dataset("d1")
    b = a.create_group("b")
    _ = b.create_dataset("d2")
    c = b.create_group("c")
    z = root.create_group("x/y/z")
    d = c.create_group("d")
    _ = a.create_dataset("d3")
    _ = root.create_dataset("d4")
    _ = d.create_dataset("d5")
    _ = d.create_dataset("d6")
    d7 = root.create_dataset("d7")

    assert len(root) == 14
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 7
    assert "a" in root
    assert "d1" in root.a
    assert "b" in root.a
    assert "d2" in root.a.b
    assert "c" in root.a.b
    assert "x" in root
    assert "x/y" in root
    assert "y" in root.x
    assert "x/y/z" in root
    assert "z" in root.x.y
    assert "d" in root.a.b.c
    assert "/a/d3" in root
    assert "d4" in root
    assert "/d5" in root.a.b.c.d
    assert "/a/b/c/d/d6" in root
    assert "d7" in root

    # remove the 'd7' Dataset
    d7_2 = root.remove("d7")
    assert len(root) == 13
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 6
    assert "d7" not in root
    assert d7_2 is d7

    # remove the 'z' Group
    assert root.remove("z") is None
    assert len(root) == 13
    assert "x/y/z" in root
    assert root.remove("/y/z") is None
    assert len(root) == 13
    assert "x/y/z" in root
    z2 = root.x.remove("y/z")
    assert z2 is z
    assert len(root) == 12
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 6
    assert "/x/y/z" not in root

    # cannot remove in read-only mode
    root.read_only = True
    with pytest.raises(ValueError, match=r"read-only"):
        _ = root.remove("a")
    assert len(root) == 12
    assert "a" in root

    # remove Group 'd' (which also removes the 'd5' and 'd6' Datasets)
    root.a.b.c.read_only = False
    d2 = root.a.b.c.remove("d")
    assert len(root) == 9
    assert len(root.a) == 5
    assert len(list(root.a.groups())) == 2
    assert len(list(root.a.datasets())) == 3
    assert len(root.a.b) == 2
    assert len(list(root.a.b.groups())) == 1
    assert len(list(root.a.b.datasets())) == 1
    assert "d" not in root.a.b.c
    assert "/d" not in root.a.b.c
    assert "/a/b/c/d" not in root
    assert "/b/c/d" not in root.a
    assert "/c/d" not in root.a.b
    assert "d/d5" not in root.a.b.c
    assert "d/d6" not in root.a.b.c
    assert "c/d/d5" not in root.a.b
    assert "c/d/d6" not in root.a.b
    assert "b/c/d/d5" not in root.a
    assert "b/c/d/d6" not in root.a
    assert "a/b/c/d/d5" not in root
    assert "a/b/c/d/d6" not in root
    assert d2 is d
    with pytest.raises(ValueError, match=r"read-only"):  # root.a.b is still in read-only mode
        _ = root.a.b.remove("c")

    # remove Group 'a'
    root.read_only = False
    a2 = root.remove("a")
    assert len(root) == 3
    assert len(list(root.groups())) == 2
    assert len(list(root.datasets())) == 1
    assert a2 is a
    assert "a" not in root
    assert "d4" in root
    assert "x" in root
    assert "/x/y" in root
    assert "y" in root.x

    root.clear()
    assert len(root) == 0

    # Check that removing an Group/Dataset also removes it from the descendants
    root = Root("")
    _ = root.require_group("g1/g2/g3/g4")
    _ = root.require_dataset("g1/d0")
    d1 = root.require_dataset("g1/g2/d1")
    _ = root.require_dataset("g1/g2/d2")
    d3 = root.require_dataset("g1/g2/g3/d3")
    _ = root.require_dataset("g1/g2/g3/g4/d4")

    assert len(root) == 9
    assert len(list(root.groups())) == 4
    assert len(list(root.datasets())) == 5
    assert len(root.g1) == 8
    assert len(list(root.g1.groups())) == 3
    assert len(list(root.g1.datasets())) == 5
    assert len(root.g1.g2) == 6
    assert len(list(root.g1.g2.groups())) == 2
    assert len(list(root.g1.g2.datasets())) == 4
    assert len(root.g1.g2.g3) == 3
    assert len(list(root.g1.g2.g3.groups())) == 1
    assert len(list(root.g1.g2.g3.datasets())) == 2
    assert len(root.g1.g2.g3.g4) == 1
    assert len(list(root.g1.g2.g3.g4.groups())) == 0
    assert len(list(root.g1.g2.g3.g4.datasets())) == 1

    d3_removed = root.remove("g1/g2/g3/d3")
    assert d3_removed is d3
    assert "d3" not in root["/g1/g2/g3"]
    assert "d3" not in root.g1["g2/g3"]
    assert "d3" not in root.g1.g2["/g3"]
    assert len(root) == 8
    assert len(list(root.groups())) == 4
    assert len(list(root.datasets())) == 4
    assert len(root.g1) == 7
    assert len(list(root.g1.groups())) == 3
    assert len(list(root.g1.datasets())) == 4
    assert len(root.g1.g2) == 5
    assert len(list(root.g1.g2.groups())) == 2
    assert len(list(root.g1.g2.datasets())) == 3
    assert len(root.g1.g2.g3) == 2
    assert len(list(root.g1.g2.g3.groups())) == 1
    assert len(list(root.g1.g2.g3.datasets())) == 1
    assert len(root.g1.g2.g3.g4) == 1
    assert len(list(root.g1.g2.g3.g4.groups())) == 0
    assert len(list(root.g1.g2.g3.g4.datasets())) == 1

    d1_removed = root.g1.g2.remove("d1")
    assert d1_removed is d1
    assert "d1" not in root["/g1/g2"]
    assert "d1" not in root.g1["/g2"]
    assert "d1" not in root.g1.g2
    assert len(root) == 7
    assert len(list(root.groups())) == 4
    assert len(list(root.datasets())) == 3
    assert len(root.g1) == 6
    assert len(list(root.g1.groups())) == 3
    assert len(list(root.g1.datasets())) == 3
    assert len(root.g1.g2) == 4
    assert len(list(root.g1.g2.groups())) == 2
    assert len(list(root.g1.g2.datasets())) == 2
    assert len(root.g1.g2.g3) == 2
    assert len(list(root.g1.g2.g3.groups())) == 1
    assert len(list(root.g1.g2.g3.datasets())) == 1
    assert len(root.g1.g2.g3.g4) == 1
    assert len(list(root.g1.g2.g3.g4.groups())) == 0
    assert len(list(root.g1.g2.g3.g4.datasets())) == 1

    g3 = root.g1.g2.g3
    g3_removed = root.remove("/g1/g2/g3")
    assert g3 is g3_removed
    assert g3 not in root["/g1/g2"]
    assert g3 not in root.g1["g2"]
    assert len(root) == 4
    assert len(list(root.groups())) == 2
    assert len(list(root.datasets())) == 2
    assert len(root.g1) == 3
    assert len(list(root.g1.groups())) == 1
    assert len(list(root.g1.datasets())) == 2
    assert len(root.g1.g2) == 1
    assert len(list(root.g1.g2.groups())) == 0
    assert len(list(root.g1.g2.datasets())) == 1

    g2 = root["/g1/g2"]
    g2_removed = root.g1.remove("g2")
    assert g2 is g2_removed
    assert g2 not in root["/g1"]
    assert g2 not in root.g1
    assert len(root) == 2
    assert len(list(root.groups())) == 1
    assert len(list(root.datasets())) == 1
    assert len(root.g1) == 1
    assert len(list(root.g1.groups())) == 0
    assert len(list(root.g1.datasets())) == 1

    assert root.remove("a/b/c/d") is None


def test_get_ancestors() -> None:
    root = Root("")

    assert isinstance(root.ancestors(), types.GeneratorType)
    assert len(tuple(root.ancestors())) == 0

    _ = root.create_group("a/b/c/d/e/f/g/h")
    _ = root.a.create_dataset("dataset")

    x = root.create_group("x")
    _ = x.require_group("y/z")
    _ = root.x.y.create_dataset("dataset")

    ancestors = tuple(root.a.b.c.d.ancestors())
    assert len(ancestors) == 4
    assert ancestors[0] is root.a.b.c
    assert ancestors[1] is root.a.b
    assert ancestors[2] is root.a
    assert ancestors[3] is root

    h = root.a.b.c.d.e.f.g.h
    ancestors = tuple(h.ancestors())
    assert len(ancestors) == 8
    assert ancestors[0] is root.a.b.c.d.e.f.g
    assert ancestors[1] is root.a.b.c.d.e.f
    assert ancestors[2] is root.a.b.c.d.e
    assert ancestors[3] is root.a.b.c.d
    assert ancestors[4] is root.a.b.c
    assert ancestors[5] is root.a.b
    assert ancestors[6] is root.a
    assert ancestors[7] is root

    ancestors = tuple(root.x.y.z.ancestors())
    assert len(ancestors) == 3
    assert ancestors[0] is root.x.y
    assert ancestors[1] is root.x
    assert ancestors[2] is root

    ancestors = tuple(root.x.ancestors())
    assert len(ancestors) == 1
    assert ancestors[0] is root


def test_remove_same_endswith() -> None:  # noqa: PLR0915
    def create_new_root() -> Root:
        r = Root("")
        _ = r.create_dataset("dset")
        a = r.create_group("a")
        _ = a.create_dataset("dset")
        b = r.create_group("b")
        _ = b.create_dataset("dset")
        c = b.create_group("c")
        _ = c.create_dataset("dset")
        _ = c.create_group("b")
        d = r.create_group("d")
        _ = d.create_dataset("dset")
        _ = d.create_group("c")
        _ = d.c.create_dataset("dset")
        e = c.create_group("e")
        _ = e.create_dataset("dset")
        return r

    root = create_new_root()
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 7
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    ref = root["/b/c/e/dset"]
    obj = root.remove("/b/c/e/dset")
    assert obj is ref
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 2
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 1
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 0
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root  # does not get removed
    assert "a" in root
    assert "dset" in root.a  # does not get removed
    assert "b" in root
    assert "dset" in root.b  # does not get removed
    assert "c" in root.b
    assert "dset" in root.b.c  # does not get removed
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d  # does not get removed
    assert "c" in root.d
    assert "dset" in root.d.c  # does not get removed
    assert "e" in root.b.c
    assert "dset" not in root.b.c.e

    root = create_new_root()
    c = root.b.c
    ref = c.dset
    obj = c.remove("/dset")
    assert obj is ref
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 2
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 1
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root  # does not get removed
    assert "a" in root
    assert "dset" in root.a  # does not get removed
    assert "b" in root
    assert "dset" in root.b  # does not get removed
    assert "c" in root.b
    assert "dset" not in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d  # does not get removed
    assert "c" in root.d
    assert "dset" in root.d.c  # does not get removed
    assert "e" in root.b.c
    assert "dset" in root.b.c.e  # does not get removed

    root = create_new_root()
    b = root.b
    ref = b.c.dset
    obj = b.remove("/c/dset")
    assert obj is ref
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 2
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 1
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root  # does not get removed
    assert "a" in root
    assert "dset" in root.a  # does not get removed
    assert "b" in root
    assert "dset" in root.b  # does not get removed
    assert "c" in root.b
    assert "dset" not in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d  # does not get removed
    assert "c" in root.d
    assert "dset" in root.d.c  # does not get removed
    assert "e" in root.b.c
    assert "dset" in root.b.c.e  # does not get removed

    root = create_new_root()
    ref = root.b.c.b
    obj = root.b.c.remove("/b")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 7
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 2
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 1
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root  # does not get removed
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" not in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    root = create_new_root()
    ref = root.b.c.b
    obj = root.remove("/b/c/b")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 7
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 2
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 1
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root  # does not get removed
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" not in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    root = create_new_root()
    ref = root.b
    obj = root.remove("/b")
    assert obj is ref
    assert len(list(root.groups())) == 3
    assert len(list(root.datasets())) == 4
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" not in root
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c

    root = create_new_root()
    b = root.b
    ref = root.b.c.b
    obj = b.remove("/c/b")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 7
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 2
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 1
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" not in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    root = create_new_root()
    ref = root.b.c.b
    obj = root.remove("/b/c/b")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 7
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 2
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 1
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" not in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    root = create_new_root()
    c = root.b.c
    ref = c.e
    obj = c.remove("e")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 2
    assert len(list(root.b.datasets())) == 2
    assert len(list(root.b.c.groups())) == 1
    assert len(list(root.b.c.datasets())) == 1
    assert len(list(root.d.groups())) == 1
    assert len(list(root.d.datasets())) == 2
    assert len(list(root.d.c.groups())) == 0
    assert len(list(root.d.c.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" in root.d
    assert "dset" in root.d.c
    assert "e" not in root.b.c

    root = create_new_root()
    assert root.remove("invalid") is None

    root = create_new_root()
    ref = root.d.c
    obj = root.remove("/d/c/")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 0
    assert len(list(root.d.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" not in root.d
    assert "e" in root.b.c
    assert "dset" in root.b.c.e

    root = create_new_root()
    ref = root.d.c
    obj = root.d.remove("c")
    assert obj is ref
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 6
    assert len(list(root.a.groups())) == 0
    assert len(list(root.a.datasets())) == 1
    assert len(list(root.b.groups())) == 3
    assert len(list(root.b.datasets())) == 3
    assert len(list(root.b.c.groups())) == 2
    assert len(list(root.b.c.datasets())) == 2
    assert len(list(root.b.c.e.groups())) == 0
    assert len(list(root.b.c.e.datasets())) == 1
    assert len(list(root.d.groups())) == 0
    assert len(list(root.d.datasets())) == 1
    assert "dset" in root
    assert "a" in root
    assert "dset" in root.a
    assert "b" in root
    assert "dset" in root.b
    assert "c" in root.b
    assert "dset" in root.b.c
    assert "b" in root.b.c
    assert "d" in root
    assert "dset" in root.d
    assert "c" not in root.d
    assert "e" in root.b.c
    assert "dset" in root.b.c.e
