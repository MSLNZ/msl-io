# Metadata {: #msl-io-metadata }

All [Group][msl-io-group] and [Dataset][msl-io-dataset] items contain [Metadata][msl.io.metadata.Metadata]. A [Metadata][msl.io.metadata.Metadata] item is a [dict][]{:target="_blank"} that can be made read only and it allows for accessing the *keys* of the [dict][]{:target="_blank"} as class attributes (see [Accessing Keys as Class Attributes][attribute-key-limitations] for more information).

For example, suppose that a file is [read][msl.io.read] that has the following [Metadata][msl.io.metadata.Metadata]

<!-- invisible-code-block: pycon
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
>>> root.metadata.voltage = 7.64
>>> root.add_metadata(current=10.3, current_unit="mA")
>>> root.metadata
<Metadata '/' {'voltage': 7.64, 'voltage_unit': 'V', 'current': 10.3, 'current_unit': 'mA'}>

```
