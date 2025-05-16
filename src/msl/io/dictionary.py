"""
An dict that can be made read only.
"""
from collections.abc import MutableMapping, KeysView, ItemsView, ValuesView


class Dictionary(MutableMapping):

    def __init__(self, read_only, **kwargs):
        """A :class:`dict` that can be made read only.

        Parameters
        ----------
        read_only : :class:`bool`
            Whether the underlying :class:`dict` should be created in read-only mode.
        **kwargs
            Key-value pairs that are used to create the underlying :class:`dict` object.
        """
        self._read_only = bool(read_only)
        self._mapping = dict(**kwargs)

    def __repr__(self):
        return "{" + ", ".join(f"{key!r}: {value!r}" if isinstance(value, str) else f"{key!r}: {value}" for key, value in self._mapping.items()) + "}"

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __delitem__(self, item):
        self._raise_if_read_only()
        del self._mapping[item]

    def __getitem__(self, item):
        return self._mapping[item]

    def __setitem__(self, item, value):
        self._raise_if_read_only()
        self._mapping[item] = value

    @property
    def read_only(self):
        """:class:`bool`: Whether the underlying :class:`dict` is in read-only mode."""
        return self._read_only

    @read_only.setter
    def read_only(self, value):
        self._read_only = bool(value)

    def clear(self):
        """Remove all items from the dictionary."""
        self._raise_if_read_only()
        self._mapping.clear()

    def keys(self):
        """Return a new view of the dictionary's keys."""
        return KeysView(self)

    def values(self):
        """Return a new view of the dictionary's values."""
        return ValuesView(self)

    def items(self):
        """Return a new view of the dictionary's items, i.e., (key, value) pairs."""
        return ItemsView(self)

    def _raise_if_read_only(self):
        if self._read_only:
            # numpy also raises ValueError if the ndarray is in read-only mode
            raise ValueError(f"Cannot modify {self!r}. It is accessed in read-only mode.")

    def _raise_key_error(self, key):
        raise KeyError(f"{key!r} is not in {self!r}")
