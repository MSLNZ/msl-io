# Accessing Keys as Class Attributes {: #attribute-key-limitations }

In order to access a [dict][]{:target="_blank"} `key` as a class attribute for a [Group][msl-io-group] or a [Metadata][msl-io-metadata] item or the *fieldname* of a numpy [structured array][structured_arrays]{:target="_blank"} for a [Dataset][msl-io-dataset], then the following naming rules must be followed:

* the *name* matches the [regular-expression](https://www.regular-expressions.info/){:target="_blank"} pattern ``^[a-zA-Z][a-zA-Z0-9_]*$`` &mdash; which states that the *name* must begin with a letter and is followed by zero or more alphanumeric characters or underscores

* the *name* cannot be equal to any of the following:
    - clear
    - copy
    - fromkeys
    - get
    - items
    - keys
    - pop
    - popitem
    - read_only
    - setdefault
    - update
    - values
