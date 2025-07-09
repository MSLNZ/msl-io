"""Custom types."""
# pyright: reportGeneralTypeIssues=false

from __future__ import annotations

import array
import mmap
import os
import sys
from collections.abc import Iterator, Sequence
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

T_co = TypeVar("T_co", str, bytes, covariant=True)
T_contra = TypeVar("T_contra", str, bytes, contravariant=True)


class FileLikeRead(Protocol[T_co]):
    """A [file-like object][]{:target="_blank"} for reading."""

    def __iter__(self) -> Iterator[T_co]:
        """Iterate lines from the stream."""
        ...

    def __next__(self) -> T_co:
        """Returns the next iterator item from the stream."""
        ...

    @property
    def name(self) -> Any:
        """File name."""
        ...

    def read(self, size: int | None = -1, /) -> T_co:
        """Read from the stream."""
        ...

    def readline(self) -> T_co:
        """Read a line from the stream."""
        ...

    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Change the stream position to the given byte offset."""
        ...

    def tell(self) -> int:
        """Returns the current stream position."""
        ...


ReadLike = Union[FileLikeRead[str], FileLikeRead[bytes]]  # pyright: ignore[reportDeprecated]
"""A [file-like object][]{:target="_blank"} for reading [str][]{:target="_blank"} or [bytes][]{:target="_blank"}."""


class FileLikeWrite(Protocol[T_contra]):
    """A [file-like object][]{:target="_blank"} for writing."""

    @property
    def name(self) -> Any:
        """File name."""
        ...

    def write(self, b: T_contra, /) -> int:
        """Write to the stream."""
        ...


WriteLike = Union[FileLikeWrite[str], FileLikeWrite[bytes]]  # pyright: ignore[reportDeprecated]
"""A [file-like object][]{:target="_blank"} for writing [str][]{:target="_blank"} or [bytes][]{:target="_blank"}."""


class SupportsRead(Protocol[T_co]):
    """A [file-like object][]{:target="_blank"} that has a `read` method."""

    def read(self, size: int | None = -1, /) -> T_co:
        """Read from the stream."""
        ...


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
