.. _attribute-key-limitations:

============================
Accessing Keys as Attributes
============================
In order to access a dictionary `key` as a class attribute, for a :ref:`group` or :ref:`metadata` object,
the following naming rules for a `key` need to be followed:

* the name of a `key` matches the regex pattern ``^[A-Za-z][A-Za-z0-9_]*$``
  (which states that the `key` must begin with a letter and is followed by any number of
  alphanumeric characters or underscores)
* the name of a `key` cannot be equal to any of the following:

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
