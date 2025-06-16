"""Freezable objects (can be made read only)."""

from __future__ import annotations

from collections.abc import ItemsView, KeysView, MutableMapping, ValuesView
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

VT = TypeVar("VT")


class FreezableMap(MutableMapping[str, VT]):
    """A key-value map that can be made read only."""

    def __init__(self, *, read_only: bool, **kwargs: VT) -> None:
        """A key-value map that can be made read only.

        Args:
            read_only: Whether the mapping is initially in read-only mode (frozen).
            kwargs: Key-value pairs that are used to create the underlying map object.
        """
        self._read_only: bool = bool(read_only)
        self._mapping: dict[str, VT] = dict(**kwargs)

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the map."""
        return iter(self._mapping)

    def __len__(self) -> int:
        """Returns the length of the map."""
        return len(self._mapping)

    def __delitem__(self, key: str) -> None:
        """Maybe delete an item from the map, only if the map is not in read-only mode."""
        self._raise_if_read_only()
        del self._mapping[key]

    def __getitem__(self, key: str) -> VT:
        """Returns the value of the specified key."""
        return self._mapping[key]

    def __setitem__(self, key: str, value: VT) -> None:
        """Maybe add a key-value pair to the map, only if the map is not in read-only mode."""
        self._raise_if_read_only()
        self._mapping[key] = value

    @property
    def read_only(self) -> bool:
        """[bool][] &mdash; Whether the map is in read-only mode."""
        return self._read_only

    @read_only.setter
    def read_only(self, value: bool) -> None:
        self._read_only = bool(value)

    def clear(self) -> None:
        """Maybe remove all items from the map, only if the map is not in read-only mode."""
        self._raise_if_read_only()
        self._mapping.clear()

    def keys(self) -> KeysView[str]:
        """Return a view of the map's keys."""
        return KeysView(self)

    def values(self) -> ValuesView[VT]:
        """Return a view of the map's values."""
        return ValuesView(self)

    def items(self) -> ItemsView[str, VT]:
        """Return a view of the map's items, i.e., (key, value) pairs."""
        return ItemsView(self)

    def _raise_if_read_only(self) -> None:
        if self._read_only:
            # numpy also raises ValueError if the ndarray is in read-only mode
            msg = f"Cannot modify {self!r}. It is accessed in read-only mode."
            raise ValueError(msg)
