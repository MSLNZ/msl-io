"""Provides information about data."""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from typing import Any

import numpy as np

from .freezable import FreezableMap


class Metadata(FreezableMap[Any]):
    """Provides information about data."""

    def __init__(self, *, read_only: bool, node_name: str, **kwargs: Any) -> None:
        """Provides information about data.

        !!! attention
            Do not instantiate directly. A [Metadata][] object is created automatically
            when [create_dataset][msl.io.node.Group.create_dataset] or
            [create_group][msl.io.node.Group.create_group] is called.

        Args:
            read_only: Whether [Metadata][] is initialised in read-only mode.
            node_name: The name of the node that the [Metadata][] is associated with.
            kwargs: Key-value pairs that will be used to create the mapping.
        """
        super().__init__(read_only=read_only, **kwargs)
        self._node_name: str = node_name

    def __repr__(self) -> str:
        """Returns the string representation."""
        joined = ", ".join(f"{k!r}: {v!r}" if isinstance(v, str) else f"{k!r}: {v}" for k, v in self._mapping.items())
        return f"<Metadata {self._node_name!r} {{{joined}}}>"

    def __getitem__(self, key: str) -> Any:
        """Returns the value for the specified key."""
        try:
            value = self._mapping[key]
        except KeyError:
            msg = f"{key!r} is not in {self!r}"
            raise KeyError(msg) from None
        else:
            if isinstance(value, MutableMapping):
                return Metadata(read_only=self._read_only, node_name=self._node_name, **value)
            return value

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
                # make all numpy ndarray's read only also
                for obj in self.__dict__["_mapping"].values():
                    if isinstance(obj, np.ndarray):
                        obj.setflags(write=not val)
            except KeyError:
                pass
        elif item in {"_mapping", "_node_name"}:
            self.__dict__[item] = value
        else:
            self._raise_if_read_only()
            self._mapping[item] = value

    def copy(self, read_only: bool | None = None) -> Metadata:
        """Create a copy of the [Metadata][].

        Args:
            read_only: Whether the copy should be created in read-only mode.
                If `None`, creates a copy using the mode for the [Metadata][]
                object that is being copied.

        Returns:
            A copy of the [Metadata][].
        """
        ro = self._read_only if read_only is None else read_only
        return Metadata(read_only=ro, node_name=self._node_name, **self._mapping)

    def fromkeys(self, seq: Iterable[str], value: Any = None, *, read_only: bool | None = None) -> Metadata:
        """Create a new [Metadata][] object with keys from `seq` and values set to `value`.

        Args:
            seq: Any iterable object that contains the names of the keys.
            value: The default value to use for each key.
            read_only: Whether the returned [Metadata][] object should be initialised in read-only mode.
                If `None`, uses the mode for the [Metadata][] that is used to call this method.

        Returns:
            A new [Metadata][] object.
        """
        ro = self._read_only if read_only is None else read_only
        return Metadata(read_only=ro, node_name=self._node_name, **dict.fromkeys(seq, value))
