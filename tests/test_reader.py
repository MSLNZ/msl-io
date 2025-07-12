from msl.io import Root
from msl.io.readers import JSONReader


def test_get_root() -> None:
    root = JSONReader("")
    assert isinstance(root, Root)
    assert not root.read_only


def test_instantiate() -> None:
    reader = JSONReader("aaa.bbb")
    assert reader.file == "aaa.bbb"
