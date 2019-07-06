import types

import pytest

from msl.io.base_io import Root
from msl.io.group import Group
from msl.io.dataset import Dataset


def test_instantiation():
    root = Root('some.file')
    assert root.url == 'some.file'
    assert root.name == '/'
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert len(root) == 0
    assert len(root.metadata) == 0
    assert str(root).startswith('<Root')

    root = Root('C:\\path\\to\\a\\windows.file')
    assert root.url == 'C:\\path\\to\\a\\windows.file'
    assert root.name == '/'

    root = Root(r'\\network\drive with multiple\spa ces.file')
    assert root.url == '\\\\network\\drive with multiple\\spa ces.file'
    assert root.name == '/'

    root = Root('/home/another.xxx')
    assert root.url == '/home/another.xxx'
    assert root.name == '/'
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert len(root) == 0
    assert len(root.metadata) == 0

    root = Root('/home/another.xxx', one=1, two=2, three=3)
    assert root.url == '/home/another.xxx'
    assert root.name == '/'
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert len(root) == 0
    assert root.metadata == {'one': 1, 'two': 2, 'three': 3}

    root.is_read_only = True

    # cannot add metadata
    with pytest.raises(ValueError):
        root.add_metadata(four=4, five=5)

    root.is_read_only = False
    root.add_metadata(four=4, five=5)
    assert root.metadata == {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}


def test_create_group():
    root = Root('')

    # must specify a name for the group
    with pytest.raises(TypeError):
        root.create_group(is_read_only=True)

    assert not root.is_read_only
    assert not root.metadata.is_read_only

    root.is_read_only = True

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
    root = Root('')

    # must specify a name for the dataset
    with pytest.raises(TypeError):
        root.create_dataset()

    assert not root.is_read_only
    assert not root.metadata.is_read_only

    root.is_read_only = True

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
    assert d1.size == 0
    assert d1.dtype == float
    assert len(d1.metadata) == 0
    assert 'data1' in root

    # create a dataset with shape and metadata
    d2 = root.create_dataset('data2', shape=(10, 5), one=1)
    assert d2.name == '/data2'
    assert d2.parent is root
    assert d2.shape == (10, 5)
    assert d2.size == 50
    assert d2.dtype == float
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
    root = Root('')

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
    root = Root('')

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
    root = Root('')

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
    root = Root('')

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
    root = Root('')

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


def test_auto_create_subgroups():
    root = Root('')

    assert len(list(root.groups())) == 0
    assert len(list(root.datasets())) == 0

    root.create_group('a/group2/c/group4/d/group6')
    root.create_dataset('/w/x/y/z', shape=(10,))

    # intermediate Groups get created automatically
    with pytest.raises(ValueError):
        root.create_group('a/group2/c')
    with pytest.raises(ValueError):
        root.create_group('/w/x')

    assert len(list(root.groups())) == 9

    root.a.group2.c.group4.create_group('/m/n')

    assert len(list(root.groups())) == 11

    assert 'a' in root
    assert 'group2' in root.a
    assert 'c' in root.a.group2
    assert 'group4' in root.a.group2.c
    assert 'm' in root.a.group2.c.group4
    assert 'm/n' in root.a.group2.c.group4
    assert 'n' in root.a.group2.c.group4.m
    assert 'd' in root.a.group2.c.group4
    assert 'group6' in root.a.group2.c.group4.d

    assert 'w' in root
    assert 'w/x' in root
    assert 'w/x/y' in root
    assert 'w/x/y/z' in root
    assert root.is_dataset(root['/w/x/y/z'])
    assert root['/w/x/y/z'].shape == (10,)


def test_requires():
    root = Root('')

    #
    # Groups
    #
    assert 'a' not in root

    a = root.require_group('a')
    assert root.is_group(a)
    assert 'a' in root
    assert '/a' in root
    assert root.require_group('a') is a
    assert root.require_group('/a') is a

    # group exists but adding new metadata to it
    a2 = root.require_group('a', one=1)
    assert a2 is a
    assert a.metadata.one == 1
    assert a2.metadata.one == 1

    # try to add Metadata to a Group that is read only
    root.is_read_only = True
    with pytest.raises(ValueError):
        root.require_group('a', two=2)
    # read-only mode
    with pytest.raises(ValueError):
        a.create_group('b')

    root.is_read_only = False
    b = a.create_group('b')
    with pytest.raises(ValueError):
        a.create_group('b')
    assert root.require_group('a/b') is b

    root.require_group('/a/b/c/d/e/', foo='bar')
    assert 'a' in root
    assert 'b' in a
    assert 'c' in root.a.b
    assert 'd' in root.a.b.c
    assert 'foo' not in root.metadata
    assert 'foo' not in root.a.metadata
    assert 'foo' not in root.a.b.metadata
    assert 'foo' not in root.a.b.c.metadata
    assert 'foo' not in root.a.b.c.d.metadata
    assert 'foo' in root.a.b.c.d.e.metadata
    assert root.a.b.c.d.e.metadata.foo == 'bar'

    # change the read-only value of the new sub-groups that are required
    assert not root.is_read_only
    bb = root.require_group('aa/bb', is_read_only=True, hello='world')
    assert bb is root.aa.bb
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert root.aa.is_read_only
    assert root.aa.metadata.is_read_only
    assert bb.is_read_only
    assert bb.metadata.is_read_only
    assert len(root.aa.bb.metadata) == 1
    assert root.aa.bb.metadata.hello == 'world'
    with pytest.raises(ValueError):
        bb.add_metadata(one=1)
    bb.is_read_only = False
    bb.add_metadata(one=1)
    assert len(root.aa.bb.metadata) == 2
    assert root.aa.bb.metadata.hello == 'world'
    assert root.aa.bb.metadata.one == 1
    assert root.aa.is_read_only
    assert root.aa.metadata.is_read_only
    with pytest.raises(ValueError):
        root.aa.add_metadata(two=2)

    # require root.aa.bb but change the read-only value
    assert not root.aa.bb.is_read_only
    bb2 = root.require_group('aa/bb', is_read_only=True)
    assert bb2 is root.aa.bb
    assert bb2.is_read_only
    assert root.aa.bb.is_read_only
    with pytest.raises(ValueError):
        bb2.add_metadata(three=3)

    #
    # Datasets
    #
    with pytest.raises(ValueError):
        root.require_dataset('a')  # 'a' is already a Group but we are creating a Dataset
    w = root.require_dataset('w')
    assert root.is_dataset(w)
    assert 'w' in root
    assert '/w' in root
    assert root.require_dataset('w') is w
    assert root.require_dataset('/w/') is w

    # dataset exists but adding new metadata to it
    w2 = root.require_dataset('w', one=1)
    assert w2 is w
    assert len(w2.metadata) == 1
    assert w.metadata.one == 1
    assert w2.metadata.one == 1

    # dataset exists but ignores key-value pairs that are not Metadata but are used to create the dataset
    w2 = root.require_dataset('w', shape=(10,), order=None)
    assert w2 is w
    assert len(w2.metadata) == 1
    assert w.metadata.one == 1
    assert w2.metadata.one == 1
    assert 'shape' not in w2.metadata
    assert 'order' not in w2.metadata

    # try to add Metadata to a Dataset that is read only
    root.is_read_only = True
    with pytest.raises(ValueError):
        root.require_dataset('w', two=2)
    # read-only mode
    with pytest.raises(ValueError):
        root.create_dataset('x')

    # add a Dataset to the 'a' Group
    root.is_read_only = False
    x = a.create_dataset('x')
    with pytest.raises(ValueError):
        a.create_dataset('x')
    assert root.require_dataset('/a/x') is x

    # add a Dataset to the 'b' Group, create the necessary sub-Groups automatically
    root.require_dataset('/b/x/y/z', data=[1, 2, 3, 4], foo='bar')
    assert root.is_group(root.b)
    assert root.is_group(root.b.x)
    assert root.is_group(root.b.x.y)
    assert root.is_dataset(root.b.x.y.z)
    assert 'w' in root
    assert 'b' in root
    assert 'x' in root.b
    assert 'y' in root.b.x
    assert 'z' in root.b.x.y
    assert 'foo' not in root.metadata
    assert 'foo' not in root.b.metadata
    assert 'foo' not in root.b.x.metadata
    assert 'foo' not in root.b.x.y.metadata
    assert 'foo' in root.b.x.y.z.metadata
    assert root.b.x.y.z.metadata.foo == 'bar'
    assert root.b.x.y.z.shape == (4,)
    assert root.b.x.y.z.tolist() == [1, 2, 3, 4]
    assert root.b.x.y.z.max() == 4

    # change the read-only value of the new Dataset that is required
    assert not root.is_read_only
    yy = root.require_dataset('xx/yy', is_read_only=True, hello='world')
    assert yy is root.xx.yy
    assert not root.is_read_only
    assert not root.metadata.is_read_only
    assert root.xx.is_read_only
    assert root.xx.metadata.is_read_only
    assert yy.is_read_only
    assert yy.metadata.is_read_only
    assert len(root.xx.yy.metadata) == 1
    assert root.xx.yy.metadata.hello == 'world'
    with pytest.raises(ValueError):
        yy.add_metadata(one=1)
    yy.is_read_only = False
    yy.add_metadata(one=1)
    assert len(root.xx.yy.metadata) == 2
    assert root.xx.yy.metadata.hello == 'world'
    assert root.xx.yy.metadata.one == 1
    assert root.xx.is_read_only
    assert root.xx.metadata.is_read_only
    with pytest.raises(ValueError):
        root.xx.add_metadata(two=2)

    # require root.xx.yy but change the read-only value
    assert not root.xx.yy.is_read_only
    yy2 = root.require_dataset('/xx/yy/', is_read_only=True)
    assert yy2 is root.xx.yy
    assert yy2.is_read_only
    assert root.xx.yy.is_read_only
    with pytest.raises(ValueError):
        yy2.add_metadata(three=3)


def test_tree():
    root = Root('')
    a = root.create_group('a')
    a.create_dataset('d1')
    b = a.create_group('b')
    b.create_dataset('d2')
    c = b.create_group('c')
    root.create_group('x/y/z')
    d = c.create_group('d')
    a.create_dataset('d3')
    root.create_dataset('d4')
    d.create_dataset('d5')
    d.create_dataset('d6')
    root.create_dataset('d7')

    tree = """
<Root '' (7 groups, 7 datasets, 0 metadata)>
  <Group '/a' (3 groups, 5 datasets, 0 metadata)>
    <Group '/a/b' (2 groups, 3 datasets, 0 metadata)>
      <Group '/a/b/c' (1 groups, 2 datasets, 0 metadata)>
        <Group '/a/b/c/d' (0 groups, 2 datasets, 0 metadata)>
          <Dataset '/a/b/c/d/d5' shape=(0,) dtype=<f8 (0 metadata)>
          <Dataset '/a/b/c/d/d6' shape=(0,) dtype=<f8 (0 metadata)>
      <Dataset '/a/b/d2' shape=(0,) dtype=<f8 (0 metadata)>
    <Dataset '/a/d1' shape=(0,) dtype=<f8 (0 metadata)>
    <Dataset '/a/d3' shape=(0,) dtype=<f8 (0 metadata)>
  <Dataset '/d4' shape=(0,) dtype=<f8 (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype=<f8 (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 groups, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    # Python 2.7 64-bit has shape=(0L,) and we don't care about (0L,) vs (0,)
    assert root.tree().replace('shape=(0L,)', 'shape=(0,)') == tree[1:]  # skip the first line

    # use del instead of Group.remove()
    del root.a.b.c

    tree = """
<Root '' (5 groups, 5 datasets, 0 metadata)>
  <Group '/a' (1 groups, 3 datasets, 0 metadata)>
    <Group '/a/b' (0 groups, 1 datasets, 0 metadata)>
      <Dataset '/a/b/d2' shape=(0,) dtype=<f8 (0 metadata)>
    <Dataset '/a/d1' shape=(0,) dtype=<f8 (0 metadata)>
    <Dataset '/a/d3' shape=(0,) dtype=<f8 (0 metadata)>
  <Dataset '/d4' shape=(0,) dtype=<f8 (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype=<f8 (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 groups, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    # Python 2.7 64-bit has shape=(0L,) and we don't care about (0L,) vs (0,)
    assert root.tree().replace('shape=(0L,)', 'shape=(0,)') == tree[1:]  # skip the first line

    # use Group.remove() instead of del
    root.remove('a')

    tree = """
<Root '' (3 groups, 2 datasets, 0 metadata)>
  <Dataset '/d4' shape=(0,) dtype=<f8 (0 metadata)>
  <Dataset '/d7' shape=(0,) dtype=<f8 (0 metadata)>
  <Group '/x' (2 groups, 0 datasets, 0 metadata)>
    <Group '/x/y' (1 groups, 0 datasets, 0 metadata)>
      <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    # Python 2.7 64-bit has shape=(0L,) and we don't care about (0L,) vs (0,)
    assert root.tree().replace('shape=(0L,)', 'shape=(0,)') == tree[1:]  # skip the first line

    # increase the indentation
    tree = """
<Root '' (3 groups, 2 datasets, 0 metadata)>
     <Dataset '/d4' shape=(0,) dtype=<f8 (0 metadata)>
     <Dataset '/d7' shape=(0,) dtype=<f8 (0 metadata)>
     <Group '/x' (2 groups, 0 datasets, 0 metadata)>
          <Group '/x/y' (1 groups, 0 datasets, 0 metadata)>
               <Group '/x/y/z' (0 groups, 0 datasets, 0 metadata)>"""

    # Python 2.7 64-bit has shape=(0L,) and we don't care about (0L,) vs (0,)
    assert root.tree(indent=5).replace('shape=(0L,)', 'shape=(0,)') == tree[1:]  # skip the first line


def test_add_group():
    root = Root('some file')

    for item in [dict(), tuple(), list(), None, Dataset('dset', None, False)]:
        with pytest.raises(TypeError):
            root.add_group('name', item)

    root2 = Root('New')
    assert len(root2) == 0

    #
    # add a Group that does not contain sub-Groups nor Datasets
    #

    # add to the Root Group
    root2.add_group('', root.create_group('a', one=1, foo='bar'))
    assert len(root2) == 1
    assert root2.a is not root.a
    assert '/a' in root2
    assert len(root2.a.metadata) == 2
    assert root2.a.metadata.one == 1
    assert root2.a.metadata['foo'] == 'bar'

    root2.clear()  # also tests Root.clear()
    assert len(root2) == 0

    # creates an "/B" Group and then add to it
    root2.add_group('B', root.create_group('b', two=2))
    assert len(root2) == 2
    assert root2.B.b is not root.b
    assert '/B/b' in root2
    assert 'B' in root2
    assert 'b' in root2.B
    assert '/B/b' in root2
    assert len(root2.B.metadata) == 0
    assert len(root2.B.b.metadata) == 1
    assert root2.B.b.metadata.two == 2

    root2.clear()
    assert len(root2) == 0

    # creates an "/A/B/C" Group and then add to it (add a ridiculous amount of '/')
    root2.add_group('/////A/B/C//////////', root.create_group('c', x='x', y='y'))
    assert len(root2) == 4
    assert root2.A.B.C.c is not root.c
    assert '/A' in root2
    assert 'A/B' in root2
    assert '/A/B/C' in root2
    assert '/A/B/C/c' in root2
    assert '/c' in root2.A.B.C
    assert len(root2.A.metadata) == 0
    assert len(root2.A.B.metadata) == 0
    assert len(root2.A.B.C.metadata) == 0
    assert len(root2.A.B.C.c.metadata) == 2
    assert root2.A.B.C.c.metadata.x == 'x'
    assert root2['A']['B'].C['c'].metadata['y'] == 'y'

    # verify root's tree
    assert len(root) == 3
    assert 'a' in root
    assert '/b' in root
    assert 'c' in root
    assert len(root.a.metadata) == 2
    assert root.a.metadata.one == 1
    assert root.a.metadata.foo == 'bar'
    assert len(root.b.metadata) == 1
    assert root.b.metadata.two == 2
    assert len(root.c.metadata) == 2
    assert root.c.metadata.x == 'x'
    assert root.c.metadata.y == 'y'

    # add some Datasets to root
    root.b.create_dataset('/x', data=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    root.c.create_dataset('y/z', shape=(3, 4), meta='data')
    assert 'x' in root.b
    assert 'z' in root.c.y

    # add root to root2
    root2.add_group('/old', root)
    assert len(root2) == 11
    assert '/A' in root2
    assert 'A/B' in root2
    assert '/A/B/C' in root2
    assert '/A/B/C/c' in root2
    assert '/c' in root2.A.B.C
    assert 'old' in root2
    assert 'old/a' in root2
    assert '/old/b' in root2
    assert '/old/c' in root2
    assert '/old/b/x' in root2
    assert 'y' in root2.old.c
    assert '/y/z' in root2.old.c
    assert len(root2.A.metadata) == 0
    assert len(root2.A.B.metadata) == 0
    assert len(root2.A.B.C.metadata) == 0
    assert len(root2.A.B.C.c.metadata) == 2
    assert root2.A.B.C.c.metadata.x == 'x'
    assert root2['A']['B'].C['c'].metadata['y'] == 'y'
    assert len(root2.old.a.metadata) == 2
    assert root2.old.a.metadata.one == 1
    assert root2.old.a.metadata.foo == 'bar'
    assert len(root2.old.b.metadata) == 1
    assert root2.old.b.metadata.two == 2
    assert len(root2.old.c.metadata) == 2
    assert root2.old.c.metadata.x == 'x'
    assert root2.old.c.metadata.y == 'y'
    assert len(root2.old.b.metadata) == 1
    assert root2.old.b.metadata.two == 2
    assert len(root2.old.c.metadata) == 2
    assert root2.old.c.metadata.x == 'x'
    assert root2.old['c'].metadata['y'] == 'y'
    assert len(root2.old.c.y.metadata) == 0
    assert len(root2.old.c.y.z.metadata) == 1
    assert root2.old.c.y.z.metadata.meta == 'data'
    assert root2.old.b.x.shape == (10,)
    assert root2.old.c.y.z.shape == (3, 4)

    # the Metadata is a copy
    root2.old.c.y.z.metadata.meta = 'new value'
    assert root2.old.c.y.z.metadata.meta is not root.c.y.z.metadata.meta
    assert root2.old.c.y.z.metadata.meta == 'new value'
    assert root.c.y.z.metadata.meta == 'data'

    # the data in the Dataset is a copy
    assert root2.old.b.x.data is not root.b.x.data
    assert root2.old.c.y.z.data is not root.c.y.z.data
    root2.old.b.x[:] = 1
    assert sum(root2.old.b.x.data) == 10
    for val in root.b.x.data.tolist():
        assert val == 0


def test_remove():
    root = Root('')
    a = root.create_group('a')
    a.create_dataset('d1')
    b = a.create_group('b')
    b.create_dataset('d2')
    c = b.create_group('c')
    z = root.create_group('x/y/z')
    d = c.create_group('d')
    a.create_dataset('d3')
    root.create_dataset('d4')
    d.create_dataset('d5')
    d.create_dataset('d6')
    d7 = root.create_dataset('d7')

    assert len(root) == 14
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 7
    assert 'a' in root
    assert 'd1' in root.a
    assert 'b' in root.a
    assert 'd2' in root.a.b
    assert 'c' in root.a.b
    assert 'x' in root
    assert 'x/y' in root
    assert 'y' in root.x
    assert 'x/y/z' in root
    assert 'z' in root.x.y
    assert 'd' in root.a.b.c
    assert '/a/d3' in root
    assert 'd4' in root
    assert '/d5' in root.a.b.c.d
    assert '/a/b/c/d/d6' in root
    assert 'd7' in root

    # remove the 'd7' Dataset
    d7_2 = root.remove('d7')
    assert len(root) == 13
    assert len(list(root.groups())) == 7
    assert len(list(root.datasets())) == 6
    assert 'd7' not in root
    assert d7_2 is d7

    # remove the 'z' Group
    assert root.remove('z') is None
    assert len(root) == 13
    assert 'x/y/z' in root
    assert root.remove('/y/z') is None
    assert len(root) == 13
    assert 'x/y/z' in root
    z2 = root.x.remove('y/z')
    assert z2 is z
    assert len(root) == 12
    assert len(list(root.groups())) == 6
    assert len(list(root.datasets())) == 6
    assert '/x/y/z' not in root

    # cannot remove in read-only mode
    root.is_read_only = True
    with pytest.raises(ValueError):
        root.remove('a')
    assert len(root) == 12
    assert 'a' in root

    # remove Group 'd' (which also removes the 'd5' and 'd6' Datasets)
    root.a.b.c.is_read_only = False
    d2 = root.a.b.c.remove('d')
    assert len(root) == 9
    assert len(root.a) == 5
    assert len(list(root.a.groups())) == 2
    assert len(list(root.a.datasets())) == 3
    assert len(root.a.b) == 2
    assert len(list(root.a.b.groups())) == 1
    assert len(list(root.a.b.datasets())) == 1
    assert 'd' not in root.a.b.c
    assert '/d' not in root.a.b.c
    assert '/a/b/c/d' not in root
    assert '/b/c/d' not in root.a
    assert '/c/d' not in root.a.b
    assert 'd/d5' not in root.a.b.c
    assert 'd/d6' not in root.a.b.c
    assert 'c/d/d5' not in root.a.b
    assert 'c/d/d6' not in root.a.b
    assert 'b/c/d/d5' not in root.a
    assert 'b/c/d/d6' not in root.a
    assert 'a/b/c/d/d5' not in root
    assert 'a/b/c/d/d6' not in root
    assert d2 is d
    with pytest.raises(ValueError):  # root.a.b is still in read-only mode
        root.a.b.remove('c')

    # remove Group 'a'
    root.is_read_only = False
    a2 = root.remove('a')
    assert len(root) == 3
    assert len(list(root.groups())) == 2
    assert len(list(root.datasets())) == 1
    assert a2 is a
    assert 'a' not in root
    assert 'd4' in root
    assert 'x' in root
    assert '/x/y' in root
    assert 'y' in root.x

    root.clear()
    assert len(root) == 0
