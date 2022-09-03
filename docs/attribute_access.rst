.. _attribute-key-limitations:

==================================
Accessing Keys as Class Attributes
==================================
In order to access a dictionary `key` as a class attribute, for a :ref:`msl-io-group` or a
:ref:`msl-io-metadata` object, or the `fieldnames` of a numpy array in a :ref:`msl-io-dataset`,
then the following naming rules must be followed:

* the name matches the regex pattern ``^[a-zA-Z][a-zA-Z0-9_]*$`` -- which states that the name
  must begin with a letter and is followed by zero or more alphanumeric characters or underscores

* the name cannot be equal to any of the following:

  - clear
  - copy
  - fromkeys
  - get
  - read_only
  - items
  - keys
  - pop
  - popitem
  - setdefault
  - update
  - values
