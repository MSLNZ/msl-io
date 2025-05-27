"""Custom types."""

from __future__ import annotations

import os
from typing import Protocol, TypeVar, Union  # pyright: ignore[reportDeprecated]

PathLike = Union[str, bytes, os.PathLike[str], os.PathLike[bytes]]  # pyright: ignore[reportDeprecated]
"""A [path-like object][]{:target="_blank"}."""

_T_co = TypeVar("_T_co", str, bytes, covariant=True)


class FileLike(Protocol[_T_co]):
    """A file-like object that has `read`, `tell` and `seek` methods."""

    def read(self, size: int | None = -1, /) -> _T_co: ...
    def tell(self) -> int: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...


class SupportsRead(Protocol[_T_co]):
    """A file-like object that has a `read` method."""

    def read(self, size: int | None = -1, /) -> _T_co: ...


class MediaDownloadProgress(Protocol):
    """Status of a resumable download."""

    resumable_progress: int
    """Number of bytes received so far."""

    total_size: int
    """Total number of bytes in complete download."""

    def progress(self) -> float:
        """Percent of download completed."""
        ...
