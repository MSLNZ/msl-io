# Overview

`msl-io` follows the data model used by [HDF5]{:target="_blank"} to read and write data files &mdash; where there are [Groups][msl-io-group] and [Datasets][msl-io-dataset] and each item has [Metadata][msl-io-metadata].

![hdf5_data_model.png](assets/images/hdf5_data_model.png)

The tree structure is similar to the file-system structure used by operating systems. [Groups][msl-io-group] are analogous to directories (where [Root][msl.io.base.Root] is the root [Group][msl.io.node.Group]) and [Datasets][msl-io-dataset] are analogous to files.

The data files that can be read or written are not restricted to [HDF5]{:target="_blank"} files, but any file format that has a [Reader][msl-io-readers] implemented can be read and data files can be created using any of the [Writers][msl-io-writers].

### Write a file  {: #msl-io-write }

<!-- invisible-code-block: pycon
>>> from pathlib import Path
>>> Path("my_file.h5").unlink(missing_ok=True)
>>> Path("my_file.json").unlink(missing_ok=True)
>>> Path("my_table.csv").unlink(missing_ok=True)
>>> SKIP_IF_NO_H5PY()

-->

Suppose you want to create a new [HDF5]{:target="_blank"} file. We first create an instance of [HDF5Writer][msl.io.writers.hdf5.HDF5Writer]

```pycon
>>> from msl.io import HDF5Writer
>>> h5 = HDF5Writer()

```

then we can add [Metadata][msl.io.metadata.Metadata] to the `h5` [Root][msl.io.base.Root],

```pycon
>>> h5.add_metadata(one=1, two=2)

```

create a [Dataset][msl.io.node.Dataset],

```pycon
>>> dataset1 = h5.create_dataset("dataset1", data=[1, 2, 3, 4])

```

create a [Group][msl.io.node.Group],

```pycon
>>> my_group = h5.create_group("my_group")

```

and create a [Dataset][msl.io.node.Dataset] in `my_group`

```pycon
>>> dataset2 = my_group.create_dataset("dataset2", data=[[1, 2], [3, 4]], three=3)

```

Finally, we write the file

```pycon
>>> h5.write(file="my_file.h5")

```

!!! note
    The file is not created until you call the [write][msl.io.base.Writer.write] or [save][msl.io.base.Writer.save] method.

### Read a file {: #msl-io-read }

The [read][msl.io.read] function is available to read a file. Provided that a [Reader][msl-io-readers] has been [register][msl.io.base.register]ed to read the file a [Reader][msl.io.base.Root] instance is returned. We will now read the file that we created above.

```pycon
>>> from msl.io import read
>>> root = read("my_file.h5")

```

You can print a _tree_ representation of all [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s in the [Root][msl.io.base.Root] by calling the [tree][msl.io.base.Root.tree] method

```pycon
>>> print(root.tree())
<HDF5Reader 'my_file.h5' (1 groups, 2 datasets, 2 metadata)>
  <Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
  <Group '/my_group' (0 groups, 1 datasets, 0 metadata)>
    <Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

```

Since the `root` item is a [Group][msl.io.node.Group] instance (which operates like a Python [dict][]) you can iterate over the items that are in the file

```pycon
>>> for name, node in root.items():
...     print(f"{name!r} -- {node!r}")
'/dataset1' -- <Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
'/my_group' -- <Group '/my_group' (0 groups, 1 datasets, 0 metadata)>
'/my_group/dataset2' -- <Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

```

where *node* will either be a [Group][msl.io.node.Group] or a [Dataset][msl.io.node.Dataset].

You can iterate only over the [Group][msl.io.node.Group]s that are in the file

```pycon
>>> for group in root.groups():
...     print(group)
<Group '/my_group' (0 groups, 1 datasets, 0 metadata)>

```

or iterate over the [Dataset][msl.io.node.Dataset]s

```pycon
>>> for dataset in root.datasets():
...     print(repr(dataset))
<Dataset '/dataset1' shape=(4,) dtype='<f8' (0 metadata)>
<Dataset '/my_group/dataset2' shape=(2, 2) dtype='<f8' (1 metadata)>

```

You can access the [Metadata][msl.io.metadata.Metadata] of any item through the `metadata` attribute

```pycon
>>> print(root.metadata)
<Metadata '/' {'one': 1, 'two': 2}>

```

You can access values of the [Metadata][msl.io.metadata.Metadata] as attributes

```pycon
>>> print(root.metadata.one)
1
>>> dataset2.metadata.three
3

```

or as keys

```pycon
>>> print(root.metadata["two"])
2
>>> dataset2.metadata["three"]
3

```

When `root` is returned, it is accessed in read-only mode

```pycon
>>> root.read_only
True
>>> for name, node in root.items():
...     print(f"is {name!r} in read-only mode? {node.read_only}")
is '/dataset1' in read-only mode? True
is '/my_group' in read-only mode? True
is '/my_group/dataset2' in read-only mode? True

```

If you want to edit the [Metadata][msl.io.metadata.Metadata] of `root`, or modify any [Group][msl.io.node.Group]s or [Dataset][msl.io.node.Dataset]s in `root`, then you must first set the item to be editable. Setting the read-only mode of `root` propagates that mode to all items within `root`. For example,

```pycon
>>> root.read_only = False

```

will make `root` and all sub-[Group][msl.io.node.Group]s and all sub-[Dataset][msl.io.node.Dataset]s within `root` to be editable

```pycon
>>> for name, node in root.items():
...     print(f"is {name!r} in read-only mode? {node.read_only}")
is '/dataset1' in read-only mode? False
is '/my_group' in read-only mode? False
is '/my_group/dataset2' in read-only mode? False

```

You can make only a specific item (and its descendants) editable as well. You can make `my_group` and `dataset2` to be in read-only mode by the following (recall that `root` behaves like a Python [dict][])

```pycon
>>> root["my_group"].read_only = True

```

and this will keep `root` and `dataset1` in editable mode, but change `my_group` and `dataset2` to be in read-only mode

```pycon
>>> root.read_only
False
>>> for name, node in root.items():
...     print(f"is {name!r} in read-only mode? {node.read_only}")
is '/dataset1' in read-only mode? False
is '/my_group' in read-only mode? True
is '/my_group/dataset2' in read-only mode? True

```

You can access [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s as keys or as class attributes

```pycon
>>> root["my_group"]["dataset2"].shape
(2, 2)
>>> root.my_group.dataset2.shape
(2, 2)

```

See [Accessing Keys as Class Attributes][attribute-key-limitations] for more information.

### Convert a file

You can convert between file formats using any of the [Writers][msl-io-writers]. Suppose you had an [HDF5]{:target="_blank"} file and you wanted to convert it to the [JSON]{:target="_blank"} format

```pycon
>>> from msl.io import JSONWriter
>>> h5 = read("my_file.h5")
>>> json = JSONWriter("my_file.json")
>>> json.write(root=h5)

```

### Read data from a table

The [read_table][msl.io.read_table] function will read a table from a file. A *table* has the following properties:

1. the first row is a header
2. all rows have the same number of columns
3. all values in a column have the same data type.

The returned item is a [Dataset][msl.io.node.Dataset] with the header provided as [metadata][msl.io.node.Dataset.metadata].

Suppose a file called *my_table.txt* contains the following information

<table>
   <tr>
      <th>x</th>
      <th>y</th>
      <th>z</th>
   </tr>
   <tr>
      <td>1</td>
      <td>2</td>
      <td>3</td>
   </tr>
   <tr>
      <td>4</td>
      <td>5</td>
      <td>6</td>
   </tr>
   <tr>
      <td>7</td>
      <td>8</td>
      <td>9</td>
   </tr>
</table>

<!-- invisible-code-block: pycon
>>> with open('my_table.txt', mode='wt') as f:
...    for row in [['x','y','z'],[1,2,3],[4,5,6],[7,8,9]]:
...        dump = f.write(' '.join(str(item) for item in row) + '\n')

-->

You can read this file and interact with the data using the following

```pycon
>>> from msl.io import read_table
>>> table = read_table("my_table.txt")
>>> table
<Dataset 'my_table.txt' shape=(3, 3) dtype='<f8' (1 metadata)>
>>> table.metadata
<Metadata 'my_table.txt' {'header': ['x', 'y', 'z']}>
>>> table.data
array([[1., 2., 3.],
      [4., 5., 6.],
      [7., 8., 9.]])
>>> print(table.max())
9.0

```

You can read a table from a text-based file or from a spreadsheet.

<!-- invisible-code-block: pycon
>>> import os
>>> os.remove('my_file.h5')
>>> os.remove('my_file.json')
>>> os.remove('my_table.txt')

-->

[HDF5]: https://www.hdfgroup.org/
[JSON]: https://www.json.org/
