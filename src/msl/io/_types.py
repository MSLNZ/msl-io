"""Custom types."""
# pyright: reportGeneralTypeIssues=false

from __future__ import annotations

import array
import mmap
import os
import sys
from collections.abc import Sequence
from typing import Any, Protocol, SupportsIndex, TypeVar, Union  # pyright: ignore[reportDeprecated]

from numpy import generic
from numpy.typing import NDArray

# Alternative syntax for unions requires Python 3.10 or newer for many of the types implemented below

if sys.version_info >= (3, 10):
    from types import EllipsisType
else:
    # Rely on builtins.ellipsis
    EllipsisType = ellipsis  # pyright: ignore[reportUnreachable] # noqa: F821

if sys.version_info >= (3, 12):
    from collections.abc import Buffer as _Buffer
else:
    _Buffer = Union[bytes, bytearray, memoryview, array.array[Any], mmap.mmap, NDArray[Any], generic]  # pyright: ignore[reportUnreachable]

Buffer = _Buffer
"""Object exposing the [buffer protocol][bufferobjects]{:target="_blank"}."""

PathLike = Union[str, bytes, os.PathLike[str], os.PathLike[bytes]]  # pyright: ignore[reportDeprecated]
"""A [path-like object][]{:target="_blank"}."""

ShapeLike = Union[SupportsIndex, Sequence[SupportsIndex]]  # pyright: ignore[reportDeprecated]
"""Anything that can be coerced to a shape tuple for an [ndarray][numpy.ndarray]{:target="_blank"}."""

ToIndex = Union[SupportsIndex, slice, EllipsisType, None]  # pyright: ignore[reportDeprecated]
"""Anything that can be used as the `key` for [numpy.ndarray.__setitem__][]{:target="_blank"}."""

ToIndices = Union[ToIndex, tuple[ToIndex, ...]]  # pyright: ignore[reportDeprecated]
"""Anything that can be used as the `key` for [numpy.ndarray.__setitem__][]{:target="_blank"}."""

_T_co = TypeVar("_T_co", str, bytes, covariant=True)


class FileLike(Protocol[_T_co]):
    """A [file-like object][]{:target="_blank"} that has `read`, `tell` and `seek` methods."""

    def read(self, size: int | None = -1, /) -> _T_co: ...
    def tell(self) -> int: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...


class SupportsRead(Protocol[_T_co]):
    """A [file-like object][]{:target="_blank"} that has a `read` method."""

    def read(self, size: int | None = -1, /) -> _T_co: ...


class MediaDownloadProgress(Protocol):
    """Status of a resumable [GDrive][msl.io.google_api.GDrive] download."""

    resumable_progress: int
    """[int][] &mdash; Number of bytes received so far."""

    total_size: int
    """[int][] &mdash; Total number of bytes in complete download."""

    def progress(self) -> float:
        """Percent of download completed.

        Returns:
            Download percentage.
        """
        ...
