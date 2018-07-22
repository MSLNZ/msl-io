import types

import pytest

from msl.io.root import Root
from msl.io.group import Group
from msl.io.dataset import Dataset


def test_instantiation():
    root = Root('some.file', is_read_only=True)
    assert root.url == 'some.file'
    assert root.name == '/'
    assert root.is_read_only
    assert root.metadata.is_read_only
    assert len(root) == 0
    assert len(root.metadata) == 0

    root = Root('C:\\path\\to\\a\\windows.file', is_read_only=True)
    assert root.url == 'C:\\path\\to\\a\\windows.file'
    assert root.name == '/'

    root = Root(r'\\network\drive with multiple\spa ces.file', is_read_only=True)
    assert root.url == '\\\\network\\drive with multiple\\spa ces.file'
    assert root.name == '/'

    root = Root('/home/another.xxx', is_read_only=False)
    assert root.url == '/home/another.xxx'
    assert root.name == '/'
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert len(root) == 0
    assert len(root.metadata) == 0

    root = Root('/home/another.xxx', is_read_only=True, one=1, two=2, three=3)
    assert root.url == '/home/another.xxx'
    assert root.name == '/'
    assert root.is_read_only
    assert root.metadata.is_read_only
    assert len(root) == 0
    assert 'is_read_only' not in root.metadata
    assert root.metadata == {'one': 1, 'two': 2, 'three': 3}

    # cannot add metadata
    with pytest.raises(ValueError):
        root.add_metadata(four=4, five=5)

    root.is_read_only = False
    root.add_metadata(four=4, five=5)
    assert root.metadata == {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}


def test_create_group():
    root = Root('', is_read_only=True)

    # must specify a name for the group
    with pytest.raises(TypeError):
        root.create_group(is_read_only=True)

    assert root.is_read_only
    assert root.metadata.is_read_only

    # cannot create a group since root is in read-only mode
    with pytest.raises(ValueError):
        root.create_group('xxx')

    root.is_read_only = False
    assert not root.is_read_only
    assert not root.metadata.is_read_only

    a = root.create_group('a')
    assert root.is_group(a)
    assert a.is_group(a)
    assert isinstance(a, Group)
    assert not a.is_read_only  # gets read-only value from root
    assert not a.metadata.is_read_only  # gets read-only value from root
    assert a.name == '/a'
    assert a.parent is root
    assert 'a' in root

    # set is_read_only=True to create a subgroup that is read only but root is not read only
    b = root.create_group('b', is_read_only=True)
    assert b.is_read_only
    assert b.metadata.is_read_only
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert b.name == '/b'
    assert b.parent is root
    assert 'b' in root

    # cannot set the parent because this kwarg is pop'd
    c = root.create_group('c', parent=None)
    assert c.name == '/c'
    assert c.parent is root
    assert 'c' in root
    assert len(c.metadata) == 0

    # create a subgroup with some metadata
    d = root.create_group('d', parent=None, one=1, two=2, three=3)
    assert d.name == '/d'
    assert d.parent is root
    assert 'd' in root
    assert 'parent' not in d.metadata
    assert d.metadata == {'one': 1, 'two': 2, 'three': 3}

    # check that we can make root read only again
    root.is_read_only = True
    with pytest.raises(ValueError):
        root.create_group('xxx')

    # check that the subgroups of root make sense
    assert len(root) == 4
    assert 'a' in root
    assert 'b' in root
    assert 'c' in root
    assert 'd' in root
    assert 'xxx' not in root


def test_create_dataset():
    root = Root('', is_read_only=True)

    # must specify a name for the dataset
    with pytest.raises(TypeError):
        root.create_dataset()

    assert root.is_read_only
    assert root.metadata.is_read_only

    # cannot create a dataset if root is in read-only mode
    with pytest.raises(ValueError):
        root.create_dataset('xxx')

    root.is_read_only = False
    assert not root.is_read_only
    assert not root.metadata.is_read_only

    # create an emtpy dataset (no data, no metadata)
    d1 = root.create_dataset('data1')
    assert root.is_dataset(d1)
    assert isinstance(d1, Dataset)
    assert not d1.is_read_only  # gets read-only value from root
    assert d1.name == '/data1'
    assert d1.parent is root
    assert d1.data.size == 0
    assert d1.data.dtype == float
    assert len(d1.metadata) == 0
    assert 'data1' in root

    # create a dataset with shape and metadata
    d2 = root.create_dataset('data2', shape=(10, 5), one=1)
    assert d2.name == '/data2'
    assert d2.parent is root
    assert d2.data.shape == (10, 5)
    assert d2.data.size == 50
    assert d2.data.dtype == float
    assert len(d2.metadata) == 1
    assert d2.metadata == {'one': 1}
    assert 'data2' in root

    # cannot set the parent because this kwarg is pop'd
    d3 = root.create_dataset('data3', parent=None)
    assert d3.name == '/data3'
    assert d3.parent is root
    assert 'data3' in root

    # creating a dataset in read-only mode doesn't change root's read mode
    d4 = root.create_dataset('data4', is_read_only=True)
    assert d4.is_read_only
    assert d4.metadata.is_read_only
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert 'data4' in root

    # check kwargs
    d5 = root.create_dataset('data5', parent=None, is_read_only=True, order='F', one=1, two=2, three=3)
    assert d5.name == '/data5'
    assert d5.parent is root
    assert d5.is_read_only
    assert d5.metadata.is_read_only
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert 'data5' in root
    assert 'order' not in d5.metadata
    assert d5.metadata == {'one': 1, 'two': 2, 'three': 3}

    # check that we can make root read only again
    root.is_read_only = True
    with pytest.raises(ValueError):
        root.create_dataset('xxx')

    # check that the datasets of root make sense
    assert len(root) == 5
    assert 'data1' in root
    assert 'data2' in root
    assert 'data3' in root
    assert 'data4' in root
    assert 'data5' in root
    assert 'xxx' not in root


def test_accessing_subgroups_subdatasets():
    root = Root('', is_read_only=False)

    a = root.create_group('a')
    d1 = a.create_dataset('d1')
    b = a.create_group('b')
    c = b.create_group('c')
    d = c.create_group('d')
    d2 = d.create_dataset('d2')
    d3 = d.create_dataset('d3')

    assert a is root['/a']
    assert d1 is root['/a/d1']
    assert b is root['/a/b']
    assert c is root['/a/b/c']
    assert d is root['/a/b/c/d']
    assert d2 is root['/a/b/c/d/d2']
    assert d3 is root['/a/b/c/d/d3']

    assert d1 is a['/d1']
    assert b is a['/b']
    assert c is a['/b/c']
    assert d is a['/b/c/d']
    assert d2 is a['/b/c/d/d2']
    assert d3 is a['/b/c/d/d3']

    assert c is b['/c']
    assert d is b['/c/d']
    assert d2 is b['/c/d/d2']
    assert d3 is b['/c/d/d3']

    assert d is c['/d']
    assert d2 is c['/d/d2']
    assert d3 is c['/d/d3']

    assert d2 is d['/d2']
    assert d3 is d['/d3']

    assert root.a is root['a']
    assert root.a.d1 is root['a']['d1']
    assert root.a.b is root['a']['b']
    assert root.a.b.c is root['a']['b']['c']
    assert root.a.b.c.d is root['a']['b']['c']['d']
    assert root.a.b.c.d.d2 is root['a']['b']['c']['d']['d2']
    assert root.a.b.c.d.d3 is root['a']['b']['c']['d']['d3']

    assert root['a'].b['c'].d is root['/a/b/c/d']

    assert root.a.d1 is a['d1']
    assert root.a.b is a['b']
    assert root.a.b.c is b['c']
    assert root.a.b.c.d is c['d']
    assert root.a.b.c.d.d2 is d['d2']

    aa = root.a
    assert aa.b is root.a.b
    assert aa.b is root['a']['b']

    cc = root.a.b.c
    assert cc.d is root.a.b.c.d
    assert cc['d'] is root['a']['b']['c']['d']

    with pytest.raises(KeyError):
        xxx = root['xxx']

    with pytest.raises(AttributeError):
        xxx = root.xxx


def test_in_not_in():
    root = Root('', is_read_only=False)

    a = root.create_group('a')
    a.create_dataset('first dataset')
    b = a.create_group('b')
    c = b.create_group('c')
    d = c.create_group('d')
    d.create_dataset('second dataset')

    assert 'xxx' not in root
    assert '/' not in root
    assert 'a' in root
    assert '/a' in root
    assert 'first dataset' in a
    assert '/a/first dataset' in root
    assert 'first dataset' not in root
    assert 'b' in a
    assert '/b' in a
    assert '/a/b' in root
    assert 'c' in b
    assert '/c' in b
    assert '/a/b/c' in root
    assert '/c' not in a
    assert 'd' in c
    assert '/d' in c
    assert 'second dataset' in d
    assert '/a/b/c/d/second dataset' in root


def test_read_only_propagates():
    root = Root('', is_read_only=False)

    g1 = root.create_group('g1')
    d1 = g1.create_dataset('d1')
    g2 = g1.create_group('g2')
    g3 = g2.create_group('g3')
    d3 = g3.create_dataset('d3')
    g4 = g3.create_group('g4')

    # all sub groups/datasets inherit roots read-only value
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert not g1.is_read_only
    assert not g1.metadata.is_read_only
    assert not d1.is_read_only
    assert not d1.metadata.is_read_only
    assert not g2.is_read_only
    assert not g2.metadata.is_read_only
    assert not g3.is_read_only
    assert not g3.metadata.is_read_only
    assert not d3.is_read_only
    assert not d3.metadata.is_read_only
    assert not g4.is_read_only
    assert not g4.metadata.is_read_only

    # make all sub groups/datasets read only by only changing root
    root.is_read_only = True
    assert root.is_read_only
    assert root.metadata.is_read_only
    assert g1.is_read_only
    assert g1.metadata.is_read_only
    assert d1.is_read_only
    assert d1.metadata.is_read_only
    assert g2.is_read_only
    assert g2.metadata.is_read_only
    assert g3.is_read_only
    assert g3.metadata.is_read_only
    assert d3.is_read_only
    assert d3.metadata.is_read_only
    assert g4.is_read_only
    assert g4.metadata.is_read_only

    # make all sub groups/datasets <= g2 writeable
    g2.is_read_only = False
    assert root.is_read_only
    assert root.metadata.is_read_only
    assert g1.is_read_only
    assert g1.metadata.is_read_only
    assert d1.is_read_only
    assert d1.metadata.is_read_only
    assert not g2.is_read_only
    assert not g2.metadata.is_read_only
    assert not g3.is_read_only
    assert not g3.metadata.is_read_only
    assert not d3.is_read_only
    assert not d3.metadata.is_read_only
    assert not g4.is_read_only
    assert not g4.metadata.is_read_only


def test_datasets_groups():
    root = Root('', is_read_only=False)

    d0 = root.create_dataset('d0')
    g1 = root.create_group('g1')
    d1 = g1.create_dataset('d1')
    g2 = g1.create_group('g2')
    g3 = g2.create_group('g3')
    d3 = g3.create_dataset('d3')
    g4 = g3.create_group('g4')

    # cannot create 2 sub-Groups with the same key
    with pytest.raises(ValueError):
        root.create_group('g1')

    # cannot create 2 Datasets with the same key
    with pytest.raises(ValueError):
        g3.create_group('d3')

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
        '/d0': d0,
        '/g1': g1,
        '/g1/d1': d1,
        '/g1/g2': g2,
        '/g1/g2/g3': g3,
        '/g1/g2/g3/d3': d3,
        '/g1/g2/g3/g4': g4,
    }
    for key, value in root.items():
        assert key in root_items
        assert value is root_items[key]
        del root_items[key]


def test_delete_vertex():
    root = Root('', is_read_only=False)

    root.create_group('g1')
    g2 = root.create_group('g2')
    g2.create_group('a')
    g2.create_dataset('b')
    c = g2.create_group('c')
    root.create_group('g3')
    c.create_dataset('cd1')
    c.create_dataset('cd2')
    c.create_group('cg3')

    with pytest.raises(KeyError):  # invalid key
        del root['x']

    with pytest.raises(KeyError):  # invalid key
        del root['x']['y']

    with pytest.raises(AttributeError):  # invalid attribute
        del root.x

    with pytest.raises(AttributeError):  # invalid attribute
        del root.x.y

    root.is_read_only = True

    with pytest.raises(ValueError):  # read-only mode
        del root['g1']

    with pytest.raises(ValueError):  # read-only mode
        del root.g2

    with pytest.raises(ValueError):  # read-only mode
        del root.g2.c.cd1

    assert '/g1' in root
    assert '/g2' in root
    assert '/g2/a' in root
    assert '/g2/b' in root
    assert '/g2/c' in root
    assert '/g2/c/cd1' in root
    assert '/g2/c/cd2' in root
    assert '/g2/c/cg3' in root
    assert '/g3' in root

    root.is_read_only = False

    del root['g1']
    assert '/g1' not in root
    assert '/g2' in root
    assert '/g2/a' in root
    assert '/g2/b' in root
    assert '/g2/c' in root
    assert '/g2/c/cd1' in root
    assert '/g2/c/cd2' in root
    assert '/g2/c/cg3' in root
    assert '/g3' in root

    root.is_read_only = True

    with pytest.raises(ValueError):  # read-only mode
        del root['g2']

    with pytest.raises(ValueError):  # read-only mode
        del root.g2

    with pytest.raises(ValueError):  # read-only mode
        del root.g2.c.cg3

    root.is_read_only = False

    del root['/g2/a']
    assert '/g2' in root
    assert '/g2/a' not in root
    assert '/g2/b' in root
    assert '/g2/c' in root
    assert '/g2/c/cd1' in root
    assert '/g2/c/cd2' in root
    assert '/g2/c/cg3' in root
    assert '/g3' in root

    del root['g2']['c']['cg3']
    assert '/g2' in root
    assert '/g2/b' in root
    assert '/g2/c' in root
    assert '/g2/c/cd1' in root
    assert '/g2/c/cd2' in root
    assert '/g2/c/cg3' not in root
    assert '/g3' in root

    del root.g2.b
    assert '/g2' in root
    assert '/g2/b' not in root
    assert '/g2/c' in root
    assert '/g2/c/cd1' in root
    assert '/g2/c/cd2' in root
    assert '/g3' in root

    del root['/g2']
    assert '/g2' not in root
    assert '/g2/c' not in root
    assert '/g2/c/cd1' not in root
    assert '/g2/c/cd2' not in root
    assert '/g3' in root

    del root['g3']
    assert len(root) == 0