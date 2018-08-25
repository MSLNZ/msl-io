import pytest

from msl.io.root import Root
from msl.io.vertex import Vertex


def test_instantiation():
    root = Root('', is_read_only=True)

    v = Vertex(name='this is ok', is_read_only=True, parent=root)
    assert v.is_read_only

    # must specify a name
    with pytest.raises(TypeError):
        Vertex(parent=root, is_read_only=True)

    # the name must be a non-empty string
    with pytest.raises(ValueError):
        Vertex(name='', parent=root, is_read_only=True)

    # the name cannot be the root name
    with pytest.raises(ValueError):
        Vertex(name='/', parent=root, is_read_only=True)

    # '.' character is removed -> equivalent to name=''
    with pytest.raises(ValueError):
        Vertex(name='.', parent=root, is_read_only=True)

    # name cannot be None
    with pytest.raises(ValueError):
        Vertex(name=None, parent=root, is_read_only=True)

    # '/' and '.' characters are removed
    v = Vertex(name='//hello/wor.ld', is_read_only=False, parent=root)
    assert v.name == '/helloworld'
    assert not v.is_read_only

    v = Vertex(name='/h/e/llo.universe', parent=root, is_read_only=True)
    assert v.name == '/hellouniverse'
    assert v.is_read_only

    # check that the name is forced to be unique
    with pytest.raises(ValueError):
        Vertex(name='this is ok', is_read_only=True, parent=root)
