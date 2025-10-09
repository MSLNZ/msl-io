import re

import pytest

from msl.io import Group, JSONWriter, Root


def test_datasets_exclude() -> None:  # noqa: PLR0915
    w = JSONWriter()
    assert len(list(w.datasets())) == 0

    _ = w.create_dataset("pear", data=[1, 2, 3])  # ignore leading /
    _ = w.create_dataset("/a/B/c/apple", data=[1, 2, 3])
    _ = w.create_dataset("/a/strawberry", data=[1, 2, 3])
    _ = w.create_dataset("a/b/banana", data=[1, 2, 3])  # ignore leading /
    _ = w.create_dataset("/a/melon", data=[1, 2, 3])
    _ = w.create_dataset("/a/B/c/d/e/kiwi", data=[1, 2, 3])

    # do not exclude datasets
    datasets = list(w.datasets())
    assert len(datasets) == 6
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/B/c/apple"
    assert datasets[2].name == "/a/strawberry"
    assert datasets[3].name == "/a/b/banana"
    assert datasets[4].name == "/a/melon"
    assert datasets[5].name == "/a/B/c/d/e/kiwi"

    # exclude all datasets with 'e' in the name
    datasets = list(w.datasets(exclude="e"))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/b/banana"

    # only '/a/B/c/apple' should get excluded
    datasets = list(w.datasets(exclude="ApPl", flags=re.IGNORECASE))
    assert len(datasets) == 5
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/strawberry"
    assert datasets[2].name == "/a/b/banana"
    assert datasets[3].name == "/a/melon"
    assert datasets[4].name == "/a/B/c/d/e/kiwi"

    # everything in the '/a/B' Group should get excluded
    datasets = list(w.datasets(exclude="/a/B"))
    assert len(datasets) == 4
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/strawberry"
    assert datasets[2].name == "/a/b/banana"
    assert datasets[3].name == "/a/melon"

    # everything in the '/a/B' and '/a/b' Groups should get excluded
    datasets = list(w.datasets(exclude="/a/(B|b)"))
    assert len(datasets) == 3
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/strawberry"
    assert datasets[2].name == "/a/melon"

    # look at a subGroup
    datasets = list(w["/a/B/c"].datasets())
    assert len(datasets) == 2
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/B/c/d/e/kiwi"

    datasets = list(w.a.B.c.datasets())
    assert len(datasets) == 2
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/B/c/d/e/kiwi"

    # exclude everything with an 'e'
    datasets = list(w["/a/B/c"].datasets(exclude="e"))
    assert len(datasets) == 0

    datasets = list(w.a.B.c.datasets(exclude="e"))
    assert len(datasets) == 0

    # exclude everything in the 'e/' Group
    datasets = list(w["/a/B/c"].datasets(exclude="e/"))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/B/c/apple"

    datasets = list(w.a.B.c.datasets(exclude="e/"))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/B/c/apple"


def test_datasets_include() -> None:  # noqa: PLR0915
    w = JSONWriter()
    assert len(list(w.datasets())) == 0

    _ = w.create_dataset("pear", data=[1, 2, 3])  # ignore leading /
    _ = w.create_dataset("a/B/c/apple", data=[1, 2, 3])  # ignore leading /
    _ = w.create_dataset("/a/strawberry", data=[1, 2, 3])
    _ = w.create_dataset("/a/b/banana", data=[1, 2, 3])
    _ = w.create_dataset("/a/melon", data=[1, 2, 3])
    _ = w.create_dataset("/a/B/c/d/e/kiwi", data=[1, 2, 3])

    # include all datasets
    datasets = list(w.datasets())
    assert len(datasets) == 6
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/B/c/apple"
    assert datasets[2].name == "/a/strawberry"
    assert datasets[3].name == "/a/b/banana"
    assert datasets[4].name == "/a/melon"
    assert datasets[5].name == "/a/B/c/d/e/kiwi"

    # include all datasets with 'e' in the name
    datasets = list(w.datasets(include="e"))
    assert len(datasets) == 5
    assert datasets[0].name == "/pear"
    assert datasets[1].name == "/a/B/c/apple"
    assert datasets[2].name == "/a/strawberry"
    assert datasets[3].name == "/a/melon"
    assert datasets[4].name == "/a/B/c/d/e/kiwi"

    # only '/a/B/c/apple' should get included
    datasets = list(w.datasets(include="ApPl", flags=re.IGNORECASE))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/B/c/apple"

    # everything in the '/a/B' Group should get included
    datasets = list(w.datasets(include="/a/B"))
    assert len(datasets) == 2
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/B/c/d/e/kiwi"

    # everything in the '/a/B' and '/a/b' Groups should get included
    datasets = list(w.datasets(include="/a/(B|b)"))
    assert len(datasets) == 3
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/b/banana"
    assert datasets[2].name == "/a/B/c/d/e/kiwi"

    # look at a subGroup
    datasets = list(w["/a/B/c"].datasets())
    assert len(datasets) == 2
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/B/c/d/e/kiwi"

    datasets = list(w.a.B.c.datasets())
    assert len(datasets) == 2
    assert datasets[0].name == "/a/B/c/apple"
    assert datasets[1].name == "/a/B/c/d/e/kiwi"

    # include everything with 'pear'
    datasets = list(w["/a/B/c"].datasets(include="pear"))
    assert len(datasets) == 0

    datasets = list(w.a.B.c.datasets(include="pear"))
    assert len(datasets) == 0

    datasets = list(w.datasets(include="/pear"))
    assert len(datasets) == 1
    assert datasets[0].name == "/pear"

    # include everything in the 'e/' Group
    datasets = list(w["/a/B/c"].datasets(include="e/"))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/B/c/d/e/kiwi"

    datasets = list(w.a.B.c.datasets(include="e/"))
    assert len(datasets) == 1
    assert datasets[0].name == "/a/B/c/d/e/kiwi"

    # exclude and include
    datasets = list(w["/a/B/c"].datasets(exclude="kiwi", include="e/"))
    assert len(datasets) == 0

    datasets = list(w.a.B.c.datasets(exclude="kiwi", include="e/"))
    assert len(datasets) == 0


def test_groups_exclude() -> None:  # noqa: PLR0915
    w = JSONWriter()
    assert len(list(w.groups())) == 0

    _ = w.create_group("pear")  # ignore leading /
    _ = w.create_group("a/B/c/apple")  # ignore leading /
    _ = w.create_group("/a/strawberry")
    _ = w.create_group("/a/b/banana")
    _ = w.create_group("/a/melon")
    _ = w.create_group("/a/B/c/d/e/kiwi")

    # do not exclude any Groups
    groups = list(w.groups())
    assert len(groups) == 12
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a"
    assert groups[2].name == "/a/B"
    assert groups[3].name == "/a/B/c"
    assert groups[4].name == "/a/B/c/apple"
    assert groups[5].name == "/a/strawberry"
    assert groups[6].name == "/a/b"
    assert groups[7].name == "/a/b/banana"
    assert groups[8].name == "/a/melon"
    assert groups[9].name == "/a/B/c/d"
    assert groups[10].name == "/a/B/c/d/e"
    assert groups[11].name == "/a/B/c/d/e/kiwi"

    # exclude all Groups with 'e' in the name
    groups = list(w.groups(exclude="e"))
    assert len(groups) == 6
    assert groups[0].name == "/a"
    assert groups[1].name == "/a/B"
    assert groups[2].name == "/a/B/c"
    assert groups[3].name == "/a/b"
    assert groups[4].name == "/a/b/banana"
    assert groups[5].name == "/a/B/c/d"

    # only '/a/B/c/apple' should get excluded
    groups = list(w.groups(exclude="ApPl", flags=re.IGNORECASE))
    assert len(groups) == 11
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a"
    assert groups[2].name == "/a/B"
    assert groups[3].name == "/a/B/c"
    assert groups[4].name == "/a/strawberry"
    assert groups[5].name == "/a/b"
    assert groups[6].name == "/a/b/banana"
    assert groups[7].name == "/a/melon"
    assert groups[8].name == "/a/B/c/d"
    assert groups[9].name == "/a/B/c/d/e"
    assert groups[10].name == "/a/B/c/d/e/kiwi"

    # everything in the '/a/B' Group should get excluded
    groups = list(w.groups(exclude="/a/B"))
    assert len(groups) == 6
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a"
    assert groups[2].name == "/a/strawberry"
    assert groups[3].name == "/a/b"
    assert groups[4].name == "/a/b/banana"
    assert groups[5].name == "/a/melon"

    # everything in the '/a/B' and '/a/b' Groups should get excluded
    groups = list(w.groups(exclude="/a/(B|b)"))
    assert len(groups) == 4
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a"
    assert groups[2].name == "/a/strawberry"
    assert groups[3].name == "/a/melon"

    # look at a subGroup
    groups = list(w["/a/B/c"].groups())
    assert len(groups) == 4
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"
    assert groups[3].name == "/a/B/c/d/e/kiwi"

    groups = list(w.a.B.c.groups())
    assert len(groups) == 4
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"
    assert groups[3].name == "/a/B/c/d/e/kiwi"

    # exclude everything with an 'e'
    groups = list(w["/a/B/c"].groups(exclude="e"))
    assert len(groups) == 1
    assert groups[0].name == "/a/B/c/d"

    groups = list(w.a.B.c.groups(exclude="e"))
    assert len(groups) == 1
    assert groups[0].name == "/a/B/c/d"

    # exclude everything in the 'e/' Group
    groups = list(w["/a/B/c"].groups(exclude="e/"))
    assert len(groups) == 3
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"

    groups = list(w.a.B.c.groups(exclude="e/"))
    assert len(groups) == 3
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"


def test_groups_include() -> None:  # noqa: PLR0915
    w = JSONWriter()
    assert len(list(w.groups())) == 0

    _ = w.create_group("pear")  # ignore leading /
    _ = w.create_group("a/B/c/apple")
    _ = w.create_group("/a/strawberry")
    _ = w.create_group("a/b/banana")  # ignore leading /
    _ = w.create_group("/a/melon")
    _ = w.create_group("/a/B/c/d/e/kiwi")

    # include all Groups
    groups = list(w.groups())
    assert len(groups) == 12
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a"
    assert groups[2].name == "/a/B"
    assert groups[3].name == "/a/B/c"
    assert groups[4].name == "/a/B/c/apple"
    assert groups[5].name == "/a/strawberry"
    assert groups[6].name == "/a/b"
    assert groups[7].name == "/a/b/banana"
    assert groups[8].name == "/a/melon"
    assert groups[9].name == "/a/B/c/d"
    assert groups[10].name == "/a/B/c/d/e"
    assert groups[11].name == "/a/B/c/d/e/kiwi"

    # include all Groups with 'e' in the name
    groups = list(w.groups(include="e"))
    assert len(groups) == 6
    assert groups[0].name == "/pear"
    assert groups[1].name == "/a/B/c/apple"
    assert groups[2].name == "/a/strawberry"
    assert groups[3].name == "/a/melon"
    assert groups[4].name == "/a/B/c/d/e"
    assert groups[5].name == "/a/B/c/d/e/kiwi"

    # only '/a/B/c/apple' should get included
    groups = list(w.groups(include="ApPl", flags=re.IGNORECASE))
    assert len(groups) == 1
    assert groups[0].name == "/a/B/c/apple"

    # everything in the '/a/B' Group should get included
    groups = list(w.groups(include="/a/B"))
    assert len(groups) == 6
    assert groups[0].name == "/a/B"
    assert groups[1].name == "/a/B/c"
    assert groups[2].name == "/a/B/c/apple"
    assert groups[3].name == "/a/B/c/d"
    assert groups[4].name == "/a/B/c/d/e"
    assert groups[5].name == "/a/B/c/d/e/kiwi"

    # everything in the '/a/B' and '/a/b' Groups should get included
    groups = list(w.groups(include="/a/(B|b)"))
    assert len(groups) == 8
    assert groups[0].name == "/a/B"
    assert groups[1].name == "/a/B/c"
    assert groups[2].name == "/a/B/c/apple"
    assert groups[3].name == "/a/b"
    assert groups[4].name == "/a/b/banana"
    assert groups[5].name == "/a/B/c/d"
    assert groups[6].name == "/a/B/c/d/e"
    assert groups[7].name == "/a/B/c/d/e/kiwi"

    # look at a subGroup
    groups = list(w["/a/B/c"].groups())
    assert len(groups) == 4
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"
    assert groups[3].name == "/a/B/c/d/e/kiwi"

    groups = list(w.a.B.c.groups())
    assert len(groups) == 4
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d"
    assert groups[2].name == "/a/B/c/d/e"
    assert groups[3].name == "/a/B/c/d/e/kiwi"

    # include everything with an 'e'
    groups = list(w["/a/B/c"].groups(include="e"))
    assert len(groups) == 3
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d/e"
    assert groups[2].name == "/a/B/c/d/e/kiwi"

    groups = list(w.a.B.c.groups(include="e"))
    assert len(groups) == 3
    assert groups[0].name == "/a/B/c/apple"
    assert groups[1].name == "/a/B/c/d/e"
    assert groups[2].name == "/a/B/c/d/e/kiwi"

    # include everything in the 'e/' Group
    groups = list(w["/a/B/c"].groups(include="e/"))
    assert len(groups) == 1
    assert groups[0].name == "/a/B/c/d/e/kiwi"

    groups = list(w.a.B.c.groups(include="e/"))
    assert len(groups) == 1
    assert groups[0].name == "/a/B/c/d/e/kiwi"

    # exclude and include
    groups = list(w["/a/B/c"].groups(exclude="apple", include="e"))
    assert len(groups) == 2
    assert groups[0].name == "/a/B/c/d/e"
    assert groups[1].name == "/a/B/c/d/e/kiwi"

    groups = list(w.a.B.c.groups(exclude="apple", include="e"))
    assert len(groups) == 2
    assert groups[0].name == "/a/B/c/d/e"
    assert groups[1].name == "/a/B/c/d/e/kiwi"


def test_ancestors() -> None:
    w = JSONWriter()
    assert len(list(w.ancestors())) == 0

    _ = w.create_group("pear")  # ignore leading /
    _ = w.create_group("a/B/c/apple")  # ignore leading /
    _ = w.create_group("/a/strawberry")
    _ = w.create_group("a/b/banana")  # ignore leading /
    _ = w.create_group("/a/melon")
    _ = w.create_group("/a/B/c/d/e/kiwi")

    ancestors = list(w.ancestors())
    assert len(ancestors) == 0

    ancestors = list(w.pear.ancestors())
    assert len(ancestors) == 1
    assert ancestors[0].name == "/"

    ancestors = list(w.a.ancestors())
    assert len(ancestors) == 1
    assert ancestors[0].name == "/"

    ancestors = list(w.a.B.ancestors())
    assert len(ancestors) == 2
    assert ancestors[0].name == "/a"
    assert ancestors[1].name == "/"

    ancestors = list(w.a.B.c.apple.ancestors())
    assert len(ancestors) == 4
    assert ancestors[0].name == "/a/B/c"
    assert ancestors[1].name == "/a/B"
    assert ancestors[2].name == "/a"
    assert ancestors[3].name == "/"

    ancestors = list(w["/a/B/c/d/e/kiwi"].ancestors())
    assert len(ancestors) == 6
    assert ancestors[0].name == "/a/B/c/d/e"
    assert ancestors[1].name == "/a/B/c/d"
    assert ancestors[2].name == "/a/B/c"
    assert ancestors[3].name == "/a/B"
    assert ancestors[4].name == "/a"
    assert ancestors[5].name == "/"

    ancestors = list(w["/a/B/c/d"].ancestors())
    assert len(ancestors) == 4
    assert ancestors[0].name == "/a/B/c"
    assert ancestors[1].name == "/a/B"
    assert ancestors[2].name == "/a"
    assert ancestors[3].name == "/"


def test_descendants() -> None:  # noqa: PLR0915
    w = JSONWriter()
    assert len(list(w.descendants())) == 0

    _ = w.create_group("pear")  # ignore leading /
    _ = w.create_group("a/B/c/apple")  # ignore leading /
    _ = w.create_group("/a/strawberry")
    _ = w.create_group("/a/b/banana")
    _ = w.create_group("/a/melon")
    _ = w.create_group("/a/B/c/d/e/kiwi")

    descendants = list(w.descendants())
    assert len(descendants) == 12
    assert descendants[0].name == "/pear"
    assert descendants[1].name == "/a"
    assert descendants[2].name == "/a/B"
    assert descendants[3].name == "/a/B/c"
    assert descendants[4].name == "/a/B/c/apple"
    assert descendants[5].name == "/a/strawberry"
    assert descendants[6].name == "/a/b"
    assert descendants[7].name == "/a/b/banana"
    assert descendants[8].name == "/a/melon"
    assert descendants[9].name == "/a/B/c/d"
    assert descendants[10].name == "/a/B/c/d/e"
    assert descendants[11].name == "/a/B/c/d/e/kiwi"

    descendants = list(w.pear.descendants())
    assert len(descendants) == 0

    descendants = list(w.a.descendants())
    assert len(descendants) == 10
    assert descendants[0].name == "/a/B"
    assert descendants[1].name == "/a/B/c"
    assert descendants[2].name == "/a/B/c/apple"
    assert descendants[3].name == "/a/strawberry"
    assert descendants[4].name == "/a/b"
    assert descendants[5].name == "/a/b/banana"
    assert descendants[6].name == "/a/melon"
    assert descendants[7].name == "/a/B/c/d"
    assert descendants[8].name == "/a/B/c/d/e"
    assert descendants[9].name == "/a/B/c/d/e/kiwi"

    descendants = list(w.a.B.descendants())
    assert len(descendants) == 5
    assert descendants[0].name == "/a/B/c"
    assert descendants[1].name == "/a/B/c/apple"
    assert descendants[2].name == "/a/B/c/d"
    assert descendants[3].name == "/a/B/c/d/e"
    assert descendants[4].name == "/a/B/c/d/e/kiwi"

    descendants = list(w.a.B.c.apple.descendants())
    assert len(descendants) == 0

    descendants = list(w["/a/B/c"].descendants())
    assert len(descendants) == 4
    assert descendants[0].name == "/a/B/c/apple"
    assert descendants[1].name == "/a/B/c/d"
    assert descendants[2].name == "/a/B/c/d/e"
    assert descendants[3].name == "/a/B/c/d/e/kiwi"

    descendants = list(w["a/B/c/d"].descendants())  # ignore leading /
    assert len(descendants) == 2
    assert descendants[0].name == "/a/B/c/d/e"
    assert descendants[1].name == "/a/B/c/d/e/kiwi"


def test_invalid_name() -> None:
    root = Root("")

    v = Group(name="this is ok", parent=root, read_only=True)
    assert v.read_only
    assert v.name == "/this is ok"

    # the name must be a non-empty string
    with pytest.raises(ValueError, match=r"cannot be an empty string"):
        _ = Group(name="", parent=root, read_only=True)

    # the name cannot contain a '/'
    for n in ["/", "/a", "a/b", "ab/"]:
        with pytest.raises(ValueError, match=r"cannot contain the '/' character"):
            _ = Group(name=n, parent=root, read_only=True)

    # check that the name is forced to be unique
    with pytest.raises(ValueError, match=r"is not unique"):
        _ = Group(name="this is ok", parent=root, read_only=True)


def test_eq() -> None:
    g = Group(name="a", parent=None, read_only=False, one=1)
    assert g != "a"
    assert g is not None
    assert g == Group(name="a", parent=None, read_only=True, one=1)
    assert g != Group(name="b", parent=None, read_only=True, one=1)
    assert g != Group(name="a", parent=None, read_only=True, one=1, two=2)

    _ = g.create_dataset("data", data=[1, 2, 3])
    assert g != Group(name="a", parent=None, read_only=True, one=1)

    g2 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g2.create_dataset("wrong-name", data=[1, 2, 3])
    assert g != g2

    g2 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g2.create_dataset("data", data=[1, 2, 3, 4])
    assert g != g2

    g2 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g2.create_dataset("data", data=[1, 2, 3])
    assert g == g2

    g1 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g1.create_group("b")
    g2 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g2.create_group("b")
    assert g1 == g2

    g2 = Group(name="a", parent=None, read_only=False, one=1)
    _ = g2.create_group("c")
    assert g1 != g2
