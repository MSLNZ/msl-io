# Metadata {: #msl-io-metadata }

All [Group][msl-io-group] and [Dataset][msl-io-dataset] items contain [Metadata][msl.io.metadata.Metadata]. A [Metadata][msl.io.metadata.Metadata] item is a [dict][]{:target="_blank"} that can be made read only and it allows for accessing the *keys* of the [dict][]{:target="_blank"} as class attributes (see [Accessing Keys as Class Attributes][attribute-key-limitations] for more information).

For example, suppose that a file is [read][msl.io.read] that has the following [Metadata][msl.io.metadata.Metadata]

<!-- invisible-code-block: pycon
>>> import array
>>> import numpy as np
>>> from msl.io import JSONWriter
>>> root = JSONWriter()
>>> root.add_metadata(voltage=1.2)
>>> root.add_metadata(voltage_unit='V')
>>> root.read_only = True

-->

```pycon
>>> root.metadata
<Metadata '/' {'voltage': 1.2, 'voltage_unit': 'V'}>

```

A *value* can be accessed by *key*

```pycon
>>> root.metadata["voltage"]
1.2

```

or as a class attribute

```pycon
>>> root.metadata.voltage
1.2

```

## Read/Write mode

When a file is [read][msl.io.read], the returned object is in read-only mode so you cannot modify the metadata

```pycon
>>> root.metadata.voltage = 7.64
Traceback (most recent call last):
    ...
ValueError: Cannot modify <Metadata '/' {'voltage': 1.2, 'voltage_unit': 'V'}>. It is accessed in read-only mode.

```

However, you can allow `root` to be modified by setting the [read_only][msl.io.node.Group.read_only] property to be `False`

```pycon
>>> root.metadata.read_only = False

```

and then you can modify the values

```pycon
>>> root.metadata.voltage = 7.64
>>> root.add_metadata(current=10.3, current_unit="mA")
>>> root.metadata
<Metadata '/' {'voltage': 7.64, 'voltage_unit': 'V', 'current': 10.3, 'current_unit': 'mA'}>

```

## Lists, tuples and arrays

When the metadata *value* is a [list][]{:target="_blank"}, [tuple][]{:target="_blank"} or [array.array][]{:target="_blank"}, it will automatically be converted to [numpy.ndarray][]{:target="_blank"}. The [dtype][numpy.dtype]{:target="_blank"} for a [list][]{:target="_blank"}, [tuple][]{:target="_blank"} will be [object][]{:target="_blank"}

```pycon
>>> root.metadata.temperatures = [20.1, 20.4, 19.8, 19.9]
>>> root.metadata.temperatures
array([20.1, 20.4, 19.8, 19.9], dtype=object)

```
```pycon
>>> root.metadata.humidities = (45.6, 46.1, 46.3, 44.7)
>>> root.metadata.humidities
array([45.6, 46.1, 46.3, 44.7], dtype=object)

```

and the data type used by the [array.array][]{:target="_blank"} will be preserved

```pycon
>>> root.metadata.unsigned_integers = array.array("I", [1, 2, 3, 4])
>>> root.metadata.unsigned_integers
array([1, 2, 3, 4], dtype=uint32)

```

Setting the *value* to a [ndarray][numpy.ndarray]{:target="_blank"} remains unchanged

```pycon
>>> root.metadata.eye = np.eye(2)
>>> root.metadata.eye
array([[1., 0.],
       [0., 1.]])

```

## Dictionaries

When the metadata *value* is a [dict][]{:target="_blank"} it will automatically be converted to a [Metadata][msl.io.metadata.Metadata] instance

```pycon
>>> root.metadata.nested = {"one": 1, "two": 2, "three": 3}
>>> root.metadata.nested
<Metadata '/' {'one': 1, 'two': 2, 'three': 3}>
>>> root.metadata.nested.two
2

```
