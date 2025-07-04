"""Provides information about data."""

from __future__ import annotations

from array import array
from collections.abc import Iterable, MutableMapping
from typing import Any

import numpy as np

from .freezable import FreezableMap


def _value(value: Any, *, name: str, read_only: bool = False) -> Any:
    """Maybe convert the Metadata value.

    Want builtin lists, tuples and arrays to be numpy arrays.
    The flags of an ndarray can easily be set to make it read only.
    """
    if isinstance(value, (list, tuple)):
        # Use dtype=object because it guarantees that the data types are preserved, e.g.,
        #   >>> np.asarray([True, -5, 0.002345, 'something', 49.1871524])
        #   array(['True', '-5', '0.002345', 'something', '49.1871524'], dtype='<U32')  # noqa: ERA001
        # casts every element to a string. Also, a regular Python list stores items as objects.
        a = np.asarray(value, dtype=object)
        a.setflags(write=not read_only)
        return a
    if isinstance(value, array):
        # all elements in an array.array must be the same data type, no need to use dtype=object
        a = np.asarray(value)
        a.setflags(write=not read_only)
        return a
    if isinstance(value, MutableMapping):
        return Metadata(read_only=read_only, node_name=name, **value)
    return value


class Metadata(FreezableMap[Any]):  # noqa: PLW1641
    """Provides information about data."""

    def __init__(self, *, read_only: bool, node_name: str, **kwargs: Any) -> None:
        """Provides information about data.

        !!! attention
            Do not instantiate directly. A [Metadata][msl.io.metadata.Metadata] object is created automatically
            when [create_dataset][msl.io.node.Group.create_dataset] or
            [create_group][msl.io.node.Group.create_group] is called.

        Args:
            read_only: Whether [Metadata][msl.io.metadata.Metadata] is initialised in read-only mode.
            node_name: The name of the node that the [Metadata][msl.io.metadata.Metadata] is associated with.
            kwargs: Key-value pairs that will be used to create the mapping.
        """
        meta = {k: _value(value=v, read_only=read_only, name=node_name) for k, v in kwargs.items()}
        super().__init__(read_only=read_only, **meta)
        self._node_name: str = node_name

    def __repr__(self) -> str:
        """Returns the string representation."""
        r: list[str] = []
        for k, v in self._mapping.items():
            if isinstance(v, str):
                r.append(f"{k!r}: {v!r}")
            elif isinstance(v, np.ndarray):
                a = np.array2string(v, separator=", ").replace("\n", "")
                r.append(f"{k!r}: {a}")
            else:
                r.append(f"{k!r}: {v}")
        return f"<Metadata {self._node_name!r} {{{', '.join(r)}}}>"

    def __getitem__(self, key: str) -> Any:
        """Returns the value for the specified key."""
        try:
            return self._mapping[key]
        except KeyError:
            msg = f"{key!r} is not in {self!r}"
            raise KeyError(msg) from None

    def __setitem__(self, key: str, value: Any) -> None:
        """Maybe add a key-value pair to the map, only if the map is not in read-only mode."""
        super().__setitem__(key, _value(value=value, name=self._node_name))

    def __delattr__(self, key: str) -> None:
        """Maybe delete a key-value pair, only if the mapping is not in read-only mode."""
        self._raise_if_read_only()
        try:
            del self._mapping[key]
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def __getattr__(self, key: str) -> Any:
        """Returns the value for the specified key."""
        try:
            return self.__getitem__(key)
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def __setattr__(self, item: str, value: Any) -> None:
        """Maybe set a key-value pair, only if the map is not in read-only mode."""
        if item.endswith("read_only"):
            val = bool(value)
            self.__dict__["_read_only"] = val
            try:
                for obj in self.__dict__["_mapping"].values():
                    if isinstance(obj, np.ndarray):
                        obj.setflags(write=not val)
                    elif isinstance(obj, Metadata):
                        obj.read_only = val
            except KeyError:
                pass
        elif item in {"_mapping", "_node_name"}:
            self.__dict__[item] = value
        else:
            self._raise_if_read_only()
            self._mapping[item] = _value(value=value, name=self._node_name)

    def __eq__(self, other: object, /) -> bool:  # noqa: PLR0911
        """Comparison with another Metadata instance."""
        # Do not implement __hash__ (see https://docs.python.org/3.13/reference/datamodel.html#object.__hash__)
        #
        # "If a class defines mutable objects and implements an __eq__() method, it should not implement __hash__(),
        # since the implementation of hashable collections requires that a key's hash value is immutable (if the
        # object's hash value changes, it will be in the wrong hash bucket)."
        if not isinstance(other, Metadata):
            return False

        if self._node_name != other._node_name:
            return False

        if len(self) != len(other):
            return False

        for k1, v1 in self.items():
            if k1 not in other:
                return False
            v2 = other[k1]
            if isinstance(v1, np.ndarray) or isinstance(v2, np.ndarray):
                if not np.array_equal(v1, v2):
                    return False
            elif v1 != v2:
                return False

        return True

    def copy(self, *, read_only: bool | None = None) -> Metadata:
        """Create a copy of the [Metadata][msl.io.metadata.Metadata].

        Args:
            read_only: Whether the copy should be created in read-only mode.
                If `None`, creates a copy using the mode for the [Metadata][msl.io.metadata.Metadata]
                object that is being copied.

        Returns:
            A copy of the [Metadata][msl.io.metadata.Metadata].
        """
        ro = self._read_only if read_only is None else read_only
        return Metadata(read_only=ro, node_name=self._node_name, **self._mapping)

    def fromkeys(self, seq: Iterable[str], value: Any = None, *, read_only: bool | None = None) -> Metadata:
        """Create a new [Metadata][msl.io.metadata.Metadata] object with keys from `seq` and values set to `value`.

        Args:
            seq: Any iterable object that contains the names of the keys.
            value: The default value to use for each key.
            read_only: Whether the returned [Metadata][msl.io.metadata.Metadata] object should be initialised in
            read-only mode. If `None`, uses the mode for the [Metadata][msl.io.metadata.Metadata] that is used
            to call this method.

        Returns:
            A new [Metadata][msl.io.metadata.Metadata] object.
        """
        ro = self._read_only if read_only is None else read_only
        return Metadata(read_only=ro, node_name=self._node_name, **dict.fromkeys(seq, value))
