import pytest

from msl.io.base import Root
from msl.io.vertex import Vertex


def test_instantiation() -> None:
    root = Root("")

    v = Vertex(name="this is ok", parent=root, read_only=True)
    assert v.read_only
    assert v.name == "/this is ok"

    # the name must be a non-empty string
    with pytest.raises(ValueError, match="cannot be an empty string"):
        _ = Vertex(name="", parent=root, read_only=True)

    # the name cannot contain a '/'
    for n in ["/", "/a", "a/b", "ab/"]:
        with pytest.raises(ValueError, match="cannot contain the '/' character"):
            _ = Vertex(name=n, parent=root, read_only=True)

    # check that the name is forced to be unique
    with pytest.raises(ValueError, match="is not unique"):
        _ = Vertex(name="this is ok", parent=root, read_only=True)
