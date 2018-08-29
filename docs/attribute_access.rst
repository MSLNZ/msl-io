.. _attribute-key-limitations:

============================
Accessing Keys as Attributes
============================
In order to access a dictionary `key` as a class attribute, for a :ref:`msl-io-group` or :ref:`msl-io-metadata`,
or the `fieldnames` of a numpy array in a :ref:`msl-io-dataset` the following naming rules would need to be followed:

* the name matches the regex pattern ``^[A-Za-z][A-Za-z0-9_]*$`` (which states that the name must begin with
  a letter and is followed by any number of alphanumeric characters or underscores)
* the name cannot be equal to any of the following:

  - clear
  - copy
  - fromkeys
  - get
  - is_read_only
  - items
  - keys
  - pop
  - popitem
  - setdefault
  - update
  - values
