import pytest

from msl.io.base import Root
from msl.io.base import Writer
from msl.io.vertex import Dataset


def test_set_root():
    root = Root("some file")

    writer = Writer()
    assert len(writer) == 0
    assert writer.file is None
    assert len(writer.metadata) == 0

    for item in [{}, (), [], None, Dataset(name="dset", parent=None, read_only=False)]:
        with pytest.raises(TypeError):
            writer.set_root(item)

    # set an empty root is okay
    writer.set_root(root)
    assert len(writer) == 0
    assert writer.file is None
    assert len(writer.metadata) == 0

    # set an empty root with metadata
    root = Root("some file", one=1, foo="bar")
    writer.set_root(root)
    assert len(writer) == 0
    assert writer.file is None
    assert len(writer.metadata) == 2
    assert writer.metadata.one == 1
    assert writer.metadata.foo == "bar"

    # check that the metadata gets replaced
    writer = Writer("a filename", meta="data")
    assert len(writer) == 0
    assert writer.file == "a filename"
    assert len(writer.metadata) == 1
    assert writer.metadata.meta == "data"
    writer.set_root(root)
    assert len(writer.metadata) == 2
    assert writer.metadata.one == 1
    assert writer.metadata.foo == "bar"
    assert "meta" not in writer.metadata
    assert writer.file == "a filename"  # the URL does not change

    a = root.create_group("a")
    a.create_dataset("d1")
    b = a.create_group("b")
    b.create_dataset("d2")
    c = b.create_group("c")
    root.create_group("x/y/z")
    d = c.create_group("d")
    a.create_dataset("d3")
    root.create_dataset("d4")
    d.create_dataset("d5")
    d.create_dataset("d6")
    root.create_dataset("d7")
    root.add_metadata(two=2, three=3)

    writer.set_root(root)

    assert len(writer) == 14
    assert len(list(writer.groups())) == 7
    assert len(list(writer.datasets())) == 7
    assert "a" in writer
    assert "d1" in writer.a
    assert "b" in writer.a
    assert "d2" in writer.a.b
    assert "c" in writer.a.b
    assert "x" in writer
    assert "x/y" in writer
    assert "y" in writer.x
    assert "x/y/z" in writer
    assert "z" in writer.x.y
    assert "d" in writer.a.b.c
    assert "/a/d3" in writer
    assert "d4" in writer
    assert "/d5" in writer.a.b.c.d
    assert "/a/b/c/d/d6" in writer
    assert "d7" in writer
    assert writer.a is not root.a
    assert writer.a.d1 is not root.a.d1
    assert writer.a.b is not root.a.b
    assert writer.a.b.d2 is not root.a.b.d2
    assert writer.a.b.c is not root.a.b.c
    assert writer.a.b.c.d is not root.a.b.c.d
    assert writer.a.b.c.d.d5 is not root.a.b.c.d.d5
    assert writer.a.b.c.d.d6 is not root.a.b.c.d.d6
    assert writer.a.d3 is not root.a.d3
    assert writer.d4 is not root.d4
    assert writer.d7 is not root.d7
    assert writer.x is not root.x
    assert writer.x.y is not root.x.y
    assert writer.x.y.z is not root.x.y.z
    assert len(writer.metadata) == 4
    assert writer.metadata.one == 1
    assert writer.metadata.foo == "bar"
    assert writer.metadata.two == 2
    assert writer.metadata.three == 3

    # d4 is a Dataset
    with pytest.raises(TypeError):
        writer.set_root(root.d4)

    # pass in a Group instead of a Root
    writer.set_root(root.x)
    assert len(writer) == 2
    assert len(list(writer.groups())) == 2
    assert len(list(writer.datasets())) == 0
    assert "x" not in writer
    assert "y" in writer
    assert "y/z" in writer
    assert "z" in writer.y
    assert len(writer.metadata) == 0
