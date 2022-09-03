import pytest

from msl.io.base_io import Root
from msl.io.vertex import Vertex


def test_instantiation():
    root = Root('')

    v = Vertex(name='this is ok', parent=root, read_only=True)
    assert v.read_only

    # must specify a name
    with pytest.raises(TypeError):
        Vertex(parent=root, read_only=True)

    # the name must be a non-empty string
    for n in [None, '']:
        with pytest.raises(ValueError, match=r'non-empty string'):
            Vertex(name=n, parent=root, read_only=True)

    # the name cannot contain a '/'
    for n in ['/', '/a', 'a/b']:
        with pytest.raises(ValueError, match=r'cannot contain the "/" character'):
            Vertex(name=n, parent=root, read_only=True)

    # check that the name is forced to be unique
    with pytest.raises(ValueError, match=r'is not unique'):
        Vertex(name='this is ok', parent=root, read_only=True)
