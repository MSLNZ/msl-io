# Datasets {: #msl-io-dataset }

A [Dataset][msl.io.node.Dataset] is analogous to a *file* in the file system used by an operating system and it is contained within a [Group][msl-io-group] (analogous to a *directory*).

A [Dataset][msl.io.node.Dataset] operates as a [numpy.ndarray][]{:target="_blank"} with [Metadata][msl-io-metadata] and it can be accessed in read-only mode or in read-write mode.

Since a [Dataset][msl.io.node.Dataset] is a [numpy.ndarray][]{:target="_blank"}, the attributes of an [ndarray][numpy.ndarray]{:target="_blank"} are also valid for a [Dataset][msl.io.node.Dataset]. For example, suppose `my_dataset` is a [Dataset][msl.io.node.Dataset]

<!-- invisible-code-block: pycon
>>> from msl.io import JSONWriter
>>> root = JSONWriter()
>>> data = [(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)]
>>> my_dataset = root.create_dataset('my_dataset', data=data, dtype=[('x', '<f8'), ('y', '<f8')])
>>> my_dataset.add_metadata(temperature=20.13, humidity=45.31)
>>> dset1 = root.create_dataset('dset1', data=[1, 2, 3], temperature=20.3)
>>> dset2 = root.create_dataset('dset2', data=[4, 5, 6], temperature=21.7)
>>> temperatures = root.create_dataset('temperatures', data=[19.8, 21.1, 20.5], unit="C")

-->

```pycon
>>> my_dataset
<Dataset '/my_dataset' shape=(5,) dtype='|V16' (2 metadata)>
>>> print(my_dataset)
array([(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)],
      dtype=[('x', '<f8'), ('y', '<f8')])

```

You can get the [shape][numpy.ndarray.shape]{:target="_blank"} using

```pycon
>>> my_dataset.shape
(5,)

```

or convert the data in the [Dataset][msl.io.node.Dataset] to a Python [list][]{:target="_blank"} using [tolist][numpy.ndarray.tolist]{:target="_blank"}

```pycon
>>> my_dataset.tolist()
[(0.23, 1.27), (1.86, 2.74), (3.44, 2.91), (5.91, 1.83), (8.73, 0.74)]

```

To access the [Metadata][msl-io-metadata] of a [Dataset][msl.io.node.Dataset], you access the [metadata][msl.io.node.Dataset.metadata] attribute

```pycon
>>> my_dataset.metadata
<Metadata '/my_dataset' {'temperature': 20.13, 'humidity': 45.31}>

```

You can access values of the [Metadata][msl-io-metadata] as keys

```pycon
>>> my_dataset.metadata["humidity"]
45.31

```

or as attributes

```pycon
>>> my_dataset.metadata.temperature
20.13

```

Depending on the [dtype][numpy.dtype]{:target="_blank"} that was used to create the [ndarray][numpy.ndarray]{:target="_blank"} for the [Dataset][msl.io.node.Dataset], the *field names* can also be accessed as class attributes. For example, you can access the fields in *my_dataset* as keys

```pycon
>>> my_dataset["x"]
array([0.23, 1.86, 3.44, 5.91, 8.73])

```

or as attributes

```pycon
>>> my_dataset.x
array([0.23, 1.86, 3.44, 5.91, 8.73])

```

!!! note
    The returned object is an [ndarray][numpy.ndarray]{:target="_blank"} and therefore does not contain [Metadata][msl.io.metadata.Metadata].

See [Accessing Keys as Class Attributes][attribute-key-limitations] for more information.

You can also chain multiple attribute calls together. For example, to get the maximum `x` value in `my_dataset` you can use

```pycon
>>> print(my_dataset.x.max())
8.73

```

## Slicing and Indexing

Slicing and indexing a [Dataset][msl.io.node.Dataset] is a valid operation, but returns an [ndarray][numpy.ndarray]{:target="_blank"} which does not contain [Metadata][msl-io-metadata].

Consider `my_dataset` from above. You can slice it

```pycon
>>> my_dataset[::2]
array([(0.23, 1.27), (3.44, 2.91), (8.73, 0.74)],
         dtype=[('x', '<f8'), ('y', '<f8')])

```

or index it

```pycon
>>> print(my_dataset[2])
(3.44, 2.91)

```

Since an [ndarray][numpy.ndarray]{:target="_blank"} is returned, you are responsible for keeping track of the [Metadata][msl-io-metadata] in slicing and indexing operations. For example, you can create a new [Dataset][msl.io.node.Dataset] from the subset by calling the [create_dataset][msl.io.node.Group.create_dataset] method

```pycon
>>> my_subset = root.create_dataset("my_subset", data=my_dataset[::2], **my_dataset.metadata)
>>> my_subset
<Dataset '/my_subset' shape=(3,) dtype='|V16' (2 metadata)>
>>> my_subset.data
array([(0.23, 1.27), (3.44, 2.91), (8.73, 0.74)],
         dtype=[('x', '<f8'), ('y', '<f8')])
>>> my_subset.metadata
<Metadata '/my_subset' {'temperature': 20.13, 'humidity': 45.31}>

```

## Arithmetic Operations

Arithmetic operations are valid with a [Dataset][msl.io.node.Dataset]. The returned object is a [Dataset][msl.io.node.Dataset] with all [Metadata][msl.io.metadata.Metadata] copied and the [name][msl.io.node.Dataset.name] attribute updated to represent the operation that was performed.

For example, consider a `temperatures` [Dataset][msl.io.node.Dataset]

```pycon
>>> temperatures
<Dataset '/temperatures' shape=(3,) dtype='<f8' (1 metadata)>
>>> temperatures.data
array([19.8, 21.1, 20.5])
>>> temperatures.metadata.unit
'C'

```

and you wanted to add `1` to each temperature value, you can do the following

```pycon
>>> plus_1 = temperatures + 1
>>> plus_1
<Dataset 'add(/temperatures)' shape=(3,) dtype='<f8' (1 metadata)>
>>> plus_1.data
array([20.8, 22.1, 21.5])
>>> plus_1.metadata.unit
'C'

```

!!! note
    The [name][msl.io.node.Dataset.name] attribute of the `plus_1` [Dataset][msl.io.node.Dataset] became `add(/temperatures)`.

If the arithmetic operation involves multiple [Dataset][msl.io.node.Dataset]s then the [Metadata][msl.io.metadata.Metadata] from the [Dataset][msl.io.node.Dataset]s are merged into the resultant [Dataset][msl.io.node.Dataset]. Thus, if the [Metadata][msl.io.metadata.Metadata] for the individual [Dataset][msl.io.node.Dataset]s have the same *keys* then only the key-value pair in the *right-most* [Dataset][msl.io.node.Dataset] in the operation will exist after the merger.

For example, suppose you have two [Dataset][msl.io.node.Dataset]s that contain the following information

```pycon
>>> dset1.data
array([1., 2., 3.])
>>> dset1.metadata
<Metadata '/dset1' {'temperature': 20.3}>

```

```pycon
>>> dset2.data
array([4., 5., 6.])
>>> dset2.metadata
<Metadata '/dset2' {'temperature': 21.7}>

```

You can add the [Dataset][msl.io.node.Dataset]s, but the *temperature* value in `dset2` will be merged into the [Metadata][msl.io.metadata.Metadata] of `dset3` (since `dset2` is to the *right* of `dset1` in the addition operation)

```pycon
>>> dset3 = dset1 + dset2
>>> dset3
<Dataset 'add(/dset1,/dset2)' shape=(3,) dtype='<f8' (1 metadata)>
>>> dset3.metadata
<Metadata 'add(/dset1,/dset2)' {'temperature': 21.7}>

```

If you want to preserve both temperature values, or change the resultant [name][msl.io.node.Dataset.name], you can do so by explicitly creating a new [Dataset][msl.io.node.Dataset]

```pycon
>>> dset3 = root.create_dataset("dset3", data=dset3, t1=dset1.metadata.temperature, t2=dset2.metadata.temperature)
>>> dset3
<Dataset '/dset3' shape=(3,) dtype='<f8' (2 metadata)>
>>> dset3.data
array([5., 7., 9.])
>>> dset3.metadata
<Metadata '/dset3' {'t1': 20.3, 't2': 21.7}>

```

## Logging Records

The [DatasetLogging][msl.io.node.DatasetLogging] class is a custom [Dataset][msl.io.node.Dataset] that is also a [Handler][logging.Handler]{:target="_blank"} which automatically appends [logging][]{:target="_blank"} records to the [Dataset][msl.io.node.Dataset]. See [create_dataset_logging][msl.io.node.Group.create_dataset_logging] for more details.

!!! note
    When a file is [read][msl.io.read], it will load an object that was once a [DatasetLogging][msl.io.node.DatasetLogging] as a [Dataset][msl.io.node.Dataset] (i.e., it will not be associated with new [logging][]{:target="_blank"} records that are emitted). If you want to convert the [Dataset][msl.io.node.Dataset] to be a [DatasetLogging][msl.io.node.DatasetLogging] item again, so that [logging][]{:target="_blank"} records are once again appended to it when emitted, then you must call the [require_dataset_logging][msl.io.node.Group.require_dataset_logging] method with the *name* argument equal to the value of the [name][msl.io.node.Dataset.name] attribute of the [Dataset][msl.io.node.Dataset].
