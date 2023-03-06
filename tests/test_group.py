import re

from msl.io import JSONWriter


def test_datasets_exclude():
    w = JSONWriter()
    assert len(list(w.datasets())) == 0

    w.create_dataset('pear', data=[1, 2, 3])  # ignore leading /
    w.create_dataset('/a/B/c/apple', data=[1, 2, 3])
    w.create_dataset('/a/strawberry', data=[1, 2, 3])
    w.create_dataset('a/b/banana', data=[1, 2, 3])  # ignore leading /
    w.create_dataset('/a/melon', data=[1, 2, 3])
    w.create_dataset('/a/B/c/d/e/kiwi', data=[1, 2, 3])

    # do not exclude datasets
    dsets = list(w.datasets())
    assert len(dsets) == 6
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/B/c/apple'
    assert dsets[2].name == '/a/strawberry'
    assert dsets[3].name == '/a/b/banana'
    assert dsets[4].name == '/a/melon'
    assert dsets[5].name == '/a/B/c/d/e/kiwi'

    # exclude all datasets with 'e' in the name
    dsets = list(w.datasets(exclude='e'))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/b/banana'

    # only '/a/B/c/apple' should get excluded
    dsets = list(w.datasets(exclude='ApPl', flags=re.IGNORECASE))
    assert len(dsets) == 5
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/strawberry'
    assert dsets[2].name == '/a/b/banana'
    assert dsets[3].name == '/a/melon'
    assert dsets[4].name == '/a/B/c/d/e/kiwi'

    # everything in the '/a/B' Group should get excluded
    dsets = list(w.datasets(exclude='/a/B'))
    assert len(dsets) == 4
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/strawberry'
    assert dsets[2].name == '/a/b/banana'
    assert dsets[3].name == '/a/melon'

    # everything in the '/a/B' and '/a/b' Groups should get excluded
    dsets = list(w.datasets(exclude='/a/(B|b)'))
    assert len(dsets) == 3
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/strawberry'
    assert dsets[2].name == '/a/melon'

    # look at a subGroup
    dsets = list(w['/a/B/c'].datasets())
    assert len(dsets) == 2
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/B/c/d/e/kiwi'

    dsets = list(w.a.B.c.datasets())
    assert len(dsets) == 2
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/B/c/d/e/kiwi'

    # exclude everything with an 'e'
    dsets = list(w['/a/B/c'].datasets(exclude='e'))
    assert len(dsets) == 0

    dsets = list(w.a.B.c.datasets(exclude='e'))
    assert len(dsets) == 0

    # exclude everything in the 'e/' Group
    dsets = list(w['/a/B/c'].datasets(exclude='e/'))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/B/c/apple'

    dsets = list(w.a.B.c.datasets(exclude='e/'))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/B/c/apple'


def test_datasets_include():
    w = JSONWriter()
    assert len(list(w.datasets())) == 0

    w.create_dataset('pear', data=[1, 2, 3])  # ignore leading /
    w.create_dataset('a/B/c/apple', data=[1, 2, 3])  # ignore leading /
    w.create_dataset('/a/strawberry', data=[1, 2, 3])
    w.create_dataset('/a/b/banana', data=[1, 2, 3])
    w.create_dataset('/a/melon', data=[1, 2, 3])
    w.create_dataset('/a/B/c/d/e/kiwi', data=[1, 2, 3])

    # include all datasets
    dsets = list(w.datasets())
    assert len(dsets) == 6
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/B/c/apple'
    assert dsets[2].name == '/a/strawberry'
    assert dsets[3].name == '/a/b/banana'
    assert dsets[4].name == '/a/melon'
    assert dsets[5].name == '/a/B/c/d/e/kiwi'

    # include all datasets with 'e' in the name
    dsets = list(w.datasets(include='e'))
    assert len(dsets) == 5
    assert dsets[0].name == '/pear'
    assert dsets[1].name == '/a/B/c/apple'
    assert dsets[2].name == '/a/strawberry'
    assert dsets[3].name == '/a/melon'
    assert dsets[4].name == '/a/B/c/d/e/kiwi'

    # only '/a/B/c/apple' should get included
    dsets = list(w.datasets(include='ApPl', flags=re.IGNORECASE))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/B/c/apple'

    # everything in the '/a/B' Group should get included
    dsets = list(w.datasets(include='/a/B'))
    assert len(dsets) == 2
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/B/c/d/e/kiwi'

    # everything in the '/a/B' and '/a/b' Groups should get included
    dsets = list(w.datasets(include='/a/(B|b)'))
    assert len(dsets) == 3
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/b/banana'
    assert dsets[2].name == '/a/B/c/d/e/kiwi'

    # look at a subGroup
    dsets = list(w['/a/B/c'].datasets())
    assert len(dsets) == 2
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/B/c/d/e/kiwi'

    dsets = list(w.a.B.c.datasets())
    assert len(dsets) == 2
    assert dsets[0].name == '/a/B/c/apple'
    assert dsets[1].name == '/a/B/c/d/e/kiwi'

    # include everything with 'pear'
    dsets = list(w['/a/B/c'].datasets(include='pear'))
    assert len(dsets) == 0

    dsets = list(w.a.B.c.datasets(include='pear'))
    assert len(dsets) == 0

    dsets = list(w.datasets(include='/pear'))
    assert len(dsets) == 1
    assert dsets[0].name == '/pear'

    # include everything in the 'e/' Group
    dsets = list(w['/a/B/c'].datasets(include='e/'))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/B/c/d/e/kiwi'

    dsets = list(w.a.B.c.datasets(include='e/'))
    assert len(dsets) == 1
    assert dsets[0].name == '/a/B/c/d/e/kiwi'

    # exclude and include
    dsets = list(w['/a/B/c'].datasets(exclude='kiwi', include='e/'))
    assert len(dsets) == 0

    dsets = list(w.a.B.c.datasets(exclude='kiwi', include='e/'))
    assert len(dsets) == 0


def test_groups_exclude():
    w = JSONWriter()
    assert len(list(w.groups())) == 0

    w.create_group('pear')  # ignore leading /
    w.create_group('a/B/c/apple')  # ignore leading /
    w.create_group('/a/strawberry')
    w.create_group('/a/b/banana')
    w.create_group('/a/melon')
    w.create_group('/a/B/c/d/e/kiwi')

    # do not exclude any Groups
    groups = list(w.groups())
    assert len(groups) == 12
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a'
    assert groups[2].name == '/a/B'
    assert groups[3].name == '/a/B/c'
    assert groups[4].name == '/a/B/c/apple'
    assert groups[5].name == '/a/strawberry'
    assert groups[6].name == '/a/b'
    assert groups[7].name == '/a/b/banana'
    assert groups[8].name == '/a/melon'
    assert groups[9].name == '/a/B/c/d'
    assert groups[10].name == '/a/B/c/d/e'
    assert groups[11].name == '/a/B/c/d/e/kiwi'

    # exclude all Groups with 'e' in the name
    groups = list(w.groups(exclude='e'))
    assert len(groups) == 6
    assert groups[0].name == '/a'
    assert groups[1].name == '/a/B'
    assert groups[2].name == '/a/B/c'
    assert groups[3].name == '/a/b'
    assert groups[4].name == '/a/b/banana'
    assert groups[5].name == '/a/B/c/d'

    # only '/a/B/c/apple' should get excluded
    groups = list(w.groups(exclude='ApPl', flags=re.IGNORECASE))
    assert len(groups) == 11
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a'
    assert groups[2].name == '/a/B'
    assert groups[3].name == '/a/B/c'
    assert groups[4].name == '/a/strawberry'
    assert groups[5].name == '/a/b'
    assert groups[6].name == '/a/b/banana'
    assert groups[7].name == '/a/melon'
    assert groups[8].name == '/a/B/c/d'
    assert groups[9].name == '/a/B/c/d/e'
    assert groups[10].name == '/a/B/c/d/e/kiwi'

    # everything in the '/a/B' Group should get excluded
    groups = list(w.groups(exclude='/a/B'))
    assert len(groups) == 6
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a'
    assert groups[2].name == '/a/strawberry'
    assert groups[3].name == '/a/b'
    assert groups[4].name == '/a/b/banana'
    assert groups[5].name == '/a/melon'

    # everything in the '/a/B' and '/a/b' Groups should get excluded
    groups = list(w.groups(exclude='/a/(B|b)'))
    assert len(groups) == 4
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a'
    assert groups[2].name == '/a/strawberry'
    assert groups[3].name == '/a/melon'

    # look at a subGroup
    groups = list(w['/a/B/c'].groups())
    assert len(groups) == 4
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'
    assert groups[3].name == '/a/B/c/d/e/kiwi'

    groups = list(w.a.B.c.groups())
    assert len(groups) == 4
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'
    assert groups[3].name == '/a/B/c/d/e/kiwi'

    # exclude everything with an 'e'
    groups = list(w['/a/B/c'].groups(exclude='e'))
    assert len(groups) == 1
    assert groups[0].name == '/a/B/c/d'

    groups = list(w.a.B.c.groups(exclude='e'))
    assert len(groups) == 1
    assert groups[0].name == '/a/B/c/d'

    # exclude everything in the 'e/' Group
    groups = list(w['/a/B/c'].groups(exclude='e/'))
    assert len(groups) == 3
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'

    groups = list(w.a.B.c.groups(exclude='e/'))
    assert len(groups) == 3
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'


def test_groups_include():
    w = JSONWriter()
    assert len(list(w.groups())) == 0

    w.create_group('pear')  # ignore leading /
    w.create_group('a/B/c/apple')
    w.create_group('/a/strawberry')
    w.create_group('a/b/banana')  # ignore leading /
    w.create_group('/a/melon')
    w.create_group('/a/B/c/d/e/kiwi')

    # include all Groups
    groups = list(w.groups())
    assert len(groups) == 12
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a'
    assert groups[2].name == '/a/B'
    assert groups[3].name == '/a/B/c'
    assert groups[4].name == '/a/B/c/apple'
    assert groups[5].name == '/a/strawberry'
    assert groups[6].name == '/a/b'
    assert groups[7].name == '/a/b/banana'
    assert groups[8].name == '/a/melon'
    assert groups[9].name == '/a/B/c/d'
    assert groups[10].name == '/a/B/c/d/e'
    assert groups[11].name == '/a/B/c/d/e/kiwi'

    # include all Groups with 'e' in the name
    groups = list(w.groups(include='e'))
    assert len(groups) == 6
    assert groups[0].name == '/pear'
    assert groups[1].name == '/a/B/c/apple'
    assert groups[2].name == '/a/strawberry'
    assert groups[3].name == '/a/melon'
    assert groups[4].name == '/a/B/c/d/e'
    assert groups[5].name == '/a/B/c/d/e/kiwi'

    # only '/a/B/c/apple' should get included
    groups = list(w.groups(include='ApPl', flags=re.IGNORECASE))
    assert len(groups) == 1
    assert groups[0].name == '/a/B/c/apple'

    # everything in the '/a/B' Group should get included
    groups = list(w.groups(include='/a/B'))
    assert len(groups) == 6
    assert groups[0].name == '/a/B'
    assert groups[1].name == '/a/B/c'
    assert groups[2].name == '/a/B/c/apple'
    assert groups[3].name == '/a/B/c/d'
    assert groups[4].name == '/a/B/c/d/e'
    assert groups[5].name == '/a/B/c/d/e/kiwi'

    # everything in the '/a/B' and '/a/b' Groups should get included
    groups = list(w.groups(include='/a/(B|b)'))
    assert len(groups) == 8
    assert groups[0].name == '/a/B'
    assert groups[1].name == '/a/B/c'
    assert groups[2].name == '/a/B/c/apple'
    assert groups[3].name == '/a/b'
    assert groups[4].name == '/a/b/banana'
    assert groups[5].name == '/a/B/c/d'
    assert groups[6].name == '/a/B/c/d/e'
    assert groups[7].name == '/a/B/c/d/e/kiwi'

    # look at a subGroup
    groups = list(w['/a/B/c'].groups())
    assert len(groups) == 4
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'
    assert groups[3].name == '/a/B/c/d/e/kiwi'

    groups = list(w.a.B.c.groups())
    assert len(groups) == 4
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d'
    assert groups[2].name == '/a/B/c/d/e'
    assert groups[3].name == '/a/B/c/d/e/kiwi'

    # include everything with an 'e'
    groups = list(w['/a/B/c'].groups(include='e'))
    assert len(groups) == 3
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d/e'
    assert groups[2].name == '/a/B/c/d/e/kiwi'

    groups = list(w.a.B.c.groups(include='e'))
    assert len(groups) == 3
    assert groups[0].name == '/a/B/c/apple'
    assert groups[1].name == '/a/B/c/d/e'
    assert groups[2].name == '/a/B/c/d/e/kiwi'

    # include everything in the 'e/' Group
    groups = list(w['/a/B/c'].groups(include='e/'))
    assert len(groups) == 1
    assert groups[0].name == '/a/B/c/d/e/kiwi'

    groups = list(w.a.B.c.groups(include='e/'))
    assert len(groups) == 1
    assert groups[0].name == '/a/B/c/d/e/kiwi'

    # exclude and include
    groups = list(w['/a/B/c'].groups(exclude='apple', include='e'))
    assert len(groups) == 2
    assert groups[0].name == '/a/B/c/d/e'
    assert groups[1].name == '/a/B/c/d/e/kiwi'

    groups = list(w.a.B.c.groups(exclude='apple', include='e'))
    assert len(groups) == 2
    assert groups[0].name == '/a/B/c/d/e'
    assert groups[1].name == '/a/B/c/d/e/kiwi'


def test_ancestors():
    w = JSONWriter()
    assert len(list(w.ancestors())) == 0

    w.create_group('pear')  # ignore leading /
    w.create_group('a/B/c/apple')
    w.create_group('/a/strawberry')
    w.create_group('a/b/banana')  # ignore leading /
    w.create_group('/a/melon')
    w.create_group('/a/B/c/d/e/kiwi')

    ancestors = list(w.ancestors())
    assert len(ancestors) == 0

    ancestors = list(w.pear.ancestors())
    assert len(ancestors) == 1
    assert ancestors[0].name == '/'

    ancestors = list(w.a.ancestors())
    assert len(ancestors) == 1
    assert ancestors[0].name == '/'

    ancestors = list(w.a.B.ancestors())
    assert len(ancestors) == 2
    assert ancestors[0].name == '/a'
    assert ancestors[1].name == '/'

    ancestors = list(w.a.B.c.apple.ancestors())
    assert len(ancestors) == 4
    assert ancestors[0].name == '/a/B/c'
    assert ancestors[1].name == '/a/B'
    assert ancestors[2].name == '/a'
    assert ancestors[3].name == '/'

    ancestors = list(w['/a/B/c/d/e/kiwi'].ancestors())
    assert len(ancestors) == 6
    assert ancestors[0].name == '/a/B/c/d/e'
    assert ancestors[1].name == '/a/B/c/d'
    assert ancestors[2].name == '/a/B/c'
    assert ancestors[3].name == '/a/B'
    assert ancestors[4].name == '/a'
    assert ancestors[5].name == '/'

    ancestors = list(w['/a/B/c/d'].ancestors())
    assert len(ancestors) == 4
    assert ancestors[0].name == '/a/B/c'
    assert ancestors[1].name == '/a/B'
    assert ancestors[2].name == '/a'
    assert ancestors[3].name == '/'
