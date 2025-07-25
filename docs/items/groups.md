# Groups {: #msl-io-group}

A [Group][msl.io.node.Group] is analogous to a *directory* in the file system used by an operating system. A [Group][msl.io.node.Group] can contain zero or more sub-[Group][msl.io.node.Group]s (sub-directories) and it can contain zero or more [Dataset][msl-io-dataset]s. It uses a naming convention analogous to UNIX file systems where every sub-directory is separated from its parent directory by the `/` character.

From a Python perspective, a [Group][msl.io.node.Group] operates like a [dict][]. The *keys* are the names of [Group][msl.io.node.Group] members, and the *values* are the members themselves ([Group][msl.io.node.Group] or [Dataset][msl.io.node.Dataset] objects).

<!-- invisible-code-block: pycon
>>> from msl.io import JSONWriter
>>> root = JSONWriter("example.json")
>>> c = root.create_group("a/b/c")
>>> b = root.a.b
>>> dset = c.create_dataset("dset", data=list(range(100)))
>>> root.read_only = True

-->

```pycon
>>> print(root.tree())
<JSONWriter 'example.json' (3 groups, 1 datasets, 0 metadata)>
  <Group '/a' (2 groups, 1 datasets, 0 metadata)>
    <Group '/a/b' (1 groups, 1 datasets, 0 metadata)>
      <Group '/a/b/c' (0 groups, 1 datasets, 0 metadata)>
        <Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>

```

A [Group][msl.io.node.Group] can either be in read-only mode

```pycon
>>> b.create_dataset('dset_b', data=[1, 2, 3, 4])
Traceback (most recent call last):
   ...
ValueError: Cannot modify <Group '/a/b' (1 groups, 1 datasets, 0 metadata)>. It is accessed in read-only mode.

```

or in read-write mode

```pycon
>>> b.read_only = False
>>> b.create_dataset('dset_b', data=[1, 2, 3, 4])
<Dataset '/a/b/dset_b' shape=(4,) dtype='<f8' (0 metadata)>

```

The *keys* of a [Group][msl.io.node.Group] can also be accessed as class attributes

```pycon
>>> root["a"]["b"]["c"]["dset"]
<Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>
>>> root.a.b.c.dset
<Dataset '/a/b/c/dset' shape=(100,) dtype='<f8' (0 metadata)>

```

See [Accessing Keys as Class Attributes][attribute-key-limitations] for more information.

You can navigate through the tree by considering a [Group][msl.io.node.Group] to be an ancestor or descendant of other [Group][msl.io.node.Group]s

```pycon
>>> for ancestor in c.ancestors():
...    print(ancestor)
<Group '/a/b' (1 groups, 2 datasets, 0 metadata)>
<Group '/a' (2 groups, 2 datasets, 0 metadata)>
<JSONWriter 'example.json' (3 groups, 2 datasets, 0 metadata)>

```

```pycon
>>> for descendant in b.descendants():
...    print(descendant)
<Group '/a/b/c' (0 groups, 1 datasets, 0 metadata)>

```