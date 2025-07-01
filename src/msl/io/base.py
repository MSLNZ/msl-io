# noqa: D100
from __future__ import annotations

import itertools
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, overload

from .node import Group
from .utils import get_basename, is_file_readable

if TYPE_CHECKING:
    import sys
    from typing import IO, Any, Literal

    from ._types import PathLike

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="Writer")  # pyright: ignore[reportUnreachable]


logger = logging.getLogger(__package__)


class Root(Group):
    """The root [Group][msl.io.node.Group]."""

    def __init__(self, file: IO[str] | IO[bytes] | PathLike | None, **metadata: Any) -> None:
        """The root [Group][msl.io.node.Group].

        Args:
            file: The file object to associate with the [Root][msl.io.base.Root].
            metadata: All keyword arguments are used as [Metadata][msl.io.metadata.Metadata].
        """
        super().__init__(name="/", parent=None, read_only=False, **metadata)
        self._root_file: IO[str] | IO[bytes] | PathLike | None = file

    def __repr__(self) -> str:
        """Returns the string representation of the Root."""
        b = get_basename(self._root_file) if self._root_file is not None else "None"
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        return f"<{self.__class__.__name__} {b!r} ({g} groups, {d} datasets, {m} metadata)>"

    def tree(self, *, indent: int = 2) -> str:
        """Returns a representation of the [tree structure](https://en.wikipedia.org/wiki/Tree_structure).

        Shows all [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s that are in [Root][msl.io.base.Root].

        Args:
            indent: The amount of indentation to add for each recursive level.

        Returns:
            The [tree structure](https://en.wikipedia.org/wiki/Tree_structure).
        """
        return repr(self) + "\n" + "\n".join(" " * (indent * k.count("/")) + repr(v) for k, v in sorted(self.items()))


class Writer(Root, ABC):
    """Base class for an abstract Writer."""

    def __init__(self, file: IO[str] | IO[bytes] | PathLike | None = None, **metadata: Any) -> None:
        """Base class for an abstract Writer.

        Args:
            file: The file to write the data to. Can also be specified in the [write][msl.io.base.Writer.write] method.
            metadata: All keyword arguments are used as [Metadata][msl.io.metadata.Metadata].
        """
        super().__init__(file, **metadata)
        self._file: IO[str] | IO[bytes] | PathLike | None = file
        self._context_kwargs: dict[str, Any] = {}

    @property
    def file(self) -> IO[str] | IO[bytes] | PathLike | None:
        """IO[str] | IO[bytes] | PathLike | None &mdash; The file object associated with the [Writer][msl.io.base.Writer]."""  # noqa: E501
        return self._file

    def set_root(self, root: Group) -> None:
        """Set a new [Root][msl.io.base.Root] for the [Writer][msl.io.base.Writer].

        !!! attention
            This will clear the [Metadata][msl.io.metadata.Metadata] of the [Writer][msl.io.base.Writer]
            and all [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s that the
            [Writer][msl.io.base.Writer] currently contains. The `file` that was specified when
            the [Writer][msl.io.base.Writer] was created does not change.

        Args:
            root: The new `root`.
        """
        self.clear()
        self.metadata.clear()
        self.add_metadata(**root.metadata)
        if root:  # only do this if there are Groups and/or Datasets in the new root
            self.add_group("", root)

    def update_context_kwargs(self, **kwargs: Any) -> None:
        """Update the keyword arguments when used as a [context manager][with].

        When a [Writer][msl.io.base.Writer] is used as a [context manager][with] the
        [write][msl.io.base.Writer.write] method is automatically called when
        exiting the [context manager][with]. You can specify the keyword arguments
        that will be passed to the [write][msl.io.base.Writer.write] method by
        calling [update_context_kwargs][msl.io.base.Writer.update_context_kwargs]
        with the appropriate key-value pairs before the [context manager][with]
        exits. You can call this method multiple times.
        """
        self._context_kwargs.update(**kwargs)

    @abstractmethod
    def write(
        self, file: IO[str] | IO[bytes] | PathLike | None = None, root: Group | None = None, **kwargs: Any
    ) -> None:
        """Write to a file.

        !!! important
            You must override this method.

        Args:
            file: The file to write the `root` to. If `None` then uses the `file` value
                that was specified when the [Writer]msl.io.base.Writer] was instantiated.
            root: Write the `root` object in the file format of this [Writer][msl.io.base.Writer].
                This argument is useful when converting between different file formats.
            kwargs: Keyword arguments to use when writing the file.
        """

    def save(
        self, file: IO[str] | IO[bytes] | PathLike | None = None, *, root: Group | None = None, **kwargs: Any
    ) -> None:
        """Alias for [write][msl.io.base.Writer.write]."""
        self.write(file=file, root=root, **kwargs)

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter a context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        # always write the Root to the file even if
        # an exception was raised in the context manager
        self.write(**self._context_kwargs)


class Reader(Root, ABC):
    """Abstract base class for a [Reader][msl-io-readers]."""

    def __init__(self, file: IO[str] | IO[bytes] | str) -> None:
        """Abstract base class for a [Reader][msl-io-readers].

        Args:
            file: The file to read.
        """
        super().__init__(file)
        self._file: IO[str] | IO[bytes] | str = file

    @staticmethod
    @abstractmethod
    def can_read(file: IO[str] | IO[bytes] | str, **kwargs: Any) -> bool:
        """Whether this [Reader][msl.io.base.Reader] can read the file specified by `file`.

        !!! important
            You must override this method.

        Args:
            file: The file to check whether the [Reader][msl.io.base.Reader] can read it.
            kwargs: Key-value pairs that the [Reader][msl.io.base.Reader] class may need
                when checking if it can read the `file`.

        Returns:
            Either `True` (can read) or `False` (cannot read).
        """

    @property
    def file(self) -> IO[str] | IO[bytes] | str:
        """IO[str] | IO[bytes] | str &mdash; The file object associated with the [Reader][msl.io.base.Reader]."""
        return self._file

    @abstractmethod
    def read(self, **kwargs: Any) -> None:
        """Read the file.

        The file to read can be accessed by the [file][msl.io.base.Reader.file] property.

        !!! important
            You must override this method.

        Args:
            kwargs: Key-value pairs that the [Reader][msl.io.base.Reader] class may need
                when reading the file.
        """

    @overload
    @staticmethod
    def get_lines(
        file: IO[str] | PathLike,
        *lines: int | None,
        remove_empty_lines: bool = False,
        encoding: str | None = "utf-8",
        errors: Literal["strict", "ignore"] | None = "strict",
    ) -> list[str]: ...

    @overload
    @staticmethod
    def get_lines(
        file: IO[bytes],
        *lines: int | None,
        remove_empty_lines: bool = False,
        encoding: str | None = None,
        errors: Literal["strict", "ignore"] | None = None,
    ) -> list[bytes]: ...

    @staticmethod
    def get_lines(  # noqa: PLR0912
        file: IO[bytes] | IO[str] | PathLike,
        *lines: int | None,
        remove_empty_lines: bool = False,
        encoding: str | None = "utf-8",
        errors: Literal["strict", "ignore"] | None = "strict",
    ) -> list[bytes] | list[str]:
        """Return lines from a file.

        Args:
            file: The file to read lines from.
            lines: The line(s) in the file to get.
            remove_empty_lines: Whether to remove all empty lines.
            encoding: The name of the encoding to use to decode the file.
            errors: How encoding errors are to be handled.

        **Examples:**
        ```python
        get_lines(file)  # returns all lines
        get_lines(file, 5)  # returns the first 5 lines
        get_lines(file, -5)  # returns the last 5 lines
        get_lines(file, 2, 4)  # returns lines 2, 3 and 4
        get_lines(file, 2, -2)  # skips the first and last lines and returns the rest
        get_lines(file, -4, -2)  # returns the fourth-, third- and second-last lines
        get_lines(file, 1, -1, 6)  # returns every sixth line in the file
        ```

        Returns:
            The lines from the `file`. Trailing whitespace is stripped from each line.
                A [list][][[bytes][]] is returned if `file` is a file-like object
                opened in binary mode, otherwise a [list][][[str][]] is returned.
        """
        # want the "stop" line to be included
        if (len(lines) > 1) and (lines[1] is not None) and (lines[1] < 0):
            lines = (lines[0], None, *lines[2:]) if lines[1] == -1 else (lines[0], lines[1] + 1, *lines[2:])

        # want the "start" line to be included
        if (len(lines) > 1) and (lines[0] is not None) and (lines[0] > 0):
            lines = (lines[0] - 1, *lines[1:])

        result: list[bytes] | list[str]
        # itertools.islice does not support negative indices, but want to allow
        # getting the last "N" lines from a file.
        if any(val < 0 for val in lines if val):
            if isinstance(file, (bytes, str, os.PathLike)):
                with Path(os.fsdecode(file)).open(encoding=encoding, errors=errors) as f:
                    result = [line.rstrip() for line in f]
            else:
                position = file.tell()
                result = [line.rstrip() for line in file]  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
                _ = file.seek(position)

            assert lines  # noqa: S101
            if len(lines) == 1:
                result = result[lines[0] :]
            elif len(lines) == 2:  # noqa: PLR2004
                result = result[lines[0] : lines[1]]
            else:
                result = result[lines[0] : lines[1] : lines[2]]

        else:
            if not lines:
                lines = (None,)

            if isinstance(file, (bytes, str, os.PathLike)):
                with Path(os.fsdecode(file)).open(encoding=encoding, errors=errors) as f:
                    result = [line.rstrip() for line in itertools.islice(f, *lines)]
            else:
                position = file.tell()
                result = [line.rstrip() for line in itertools.islice(file, *lines)]  # type: ignore[attr-defined]  # pyright: ignore[reportAssignmentType]
                _ = file.seek(position)

        if remove_empty_lines:
            return [line for line in result if line]  # type: ignore[return-value]  # pyright: ignore[reportReturnType]
        return result

    @staticmethod
    def get_bytes(file: IO[bytes] | PathLike, *positions: int | None) -> bytes:  # noqa: C901, PLR0912, PLR0915
        """Return bytes from a file.

        Args:
            file: The file to read bytes from.
            positions: The position(s) in the file to retrieve bytes from.

        **Examples:**
        ```python
        get_bytes(file)  # returns all bytes
        get_bytes(file, 5)  # returns the first 5 bytes
        get_bytes(file, -5)  # returns the last 5 bytes
        get_bytes(file, 5, 10)  # returns bytes 5 through 10 (inclusive)
        get_bytes(file, 3, -1)  # skips the first 2 bytes and returns the rest
        get_bytes(file, -8, -4)  # returns the eighth- through fourth-last bytes (inclusive)
        get_bytes(file, 1, -1, 2)  # returns every other byte
        ```

        Returns:
            The bytes from the file.
        """
        size: int
        path: Path | None
        if isinstance(file, (bytes, str, os.PathLike)):
            path = Path(os.fsdecode(file))
            try:
                size = path.stat().st_size
            except OSError:
                # A file on a mapped network drive can raise the following:
                #   [WinError 87] The parameter is incorrect
                # for Python 3.5, 3.6 and 3.7. Also, calling os.path.getsize
                # on a file on a mapped network drive could return 0
                # (without raising OSError) on Python 3.8 and 3.9, which is
                # why we set size=0 on an OSError
                size = 0

            if size == 0:
                with path.open("rb") as f:
                    _ = f.seek(0, os.SEEK_END)
                    size = f.tell()
        else:
            path = None
            position = file.tell()
            _ = file.seek(0, os.SEEK_END)
            size = file.tell()
            _ = file.seek(position)

        if not positions:
            start, stop, step = 0, size, 1
        elif len(positions) == 1:
            start, step = 0, 1
            stop = size if positions[0] is None else positions[0]
            if stop < 0:
                start, stop = size + stop + 1, size
        elif len(positions) == 2:  # noqa: PLR2004
            start, step = positions[0] or 0, 1
            stop = size if positions[1] is None or positions[1] == -1 else positions[1]
        else:
            start, stop, step = positions[0] or 0, positions[1] or size, positions[2] or 1

        if start < 0:
            start = max(size + start, 0)
        elif start > 0:
            start -= 1
        start = min(size, start)

        if stop < 0:
            stop += size + 1
        stop = min(size, stop)

        n_bytes = max(0, stop - start)
        if isinstance(file, (bytes, str, os.PathLike)):
            assert path is not None  # noqa: S101
            with path.open("rb") as f:
                _ = f.seek(start)
                data = f.read(n_bytes)
        else:
            position = file.tell()
            _ = file.seek(start)
            data = file.read(n_bytes)
            _ = file.seek(position)

        if step != 1:
            return data[::step]
        return data

    @staticmethod
    def get_extension(file: IO[bytes] | IO[str] | PathLike) -> str:
        """Return the extension of the file.

        Args:
            file: The file to get the extension of.

        Returns:
            The extension (including the `.`).
        """
        if isinstance(file, (bytes, str, os.PathLike)):
            return Path(os.fsdecode(file)).suffix

        try:
            return Reader.get_extension(file.name)
        except AttributeError:
            return ""


def register(cls: type[Reader]) -> type[Reader]:
    """Use as a decorator to register a [Reader][msl.io.base.Reader] subclass.

    See [Create a New Reader][msl-io-create-reader] for an example on how to
    implement your own [Reader][msl-io-readers] class.

    Args:
        cls: A [Reader][msl.io.base.Reader] subclass.

    Returns:
        The (unmodified) [Reader][msl.io.base.Reader], which has been registered.
    """

    def append(_reader: type[Reader]) -> type[Reader]:
        _readers.append(cls)
        logger.debug("msl-io registered %r", cls)
        return cls

    return append(cls)


def read(file: IO[bytes] | IO[str] | PathLike, **kwargs: Any) -> Reader:
    """Read a file that has a [Reader][msl-io-readers] implemented.

    Args:
        file: The file to read.
        kwargs: All keyword arguments are passed to the abstract [can_read][msl.io.base.Reader.can_read]
            and [read][msl.io.base.Reader.read] methods.

    Returns:
        The data from the file.
    """
    if isinstance(file, (bytes, str, os.PathLike)):
        file = os.fsdecode(file)
        readable = is_file_readable(file, strict=True)
    else:
        readable = hasattr(file, "read")

    if readable:
        logger.debug("finding Reader for %r", file)
        for r in _readers:
            logger.debug("checking %s", r.__name__)
            try:
                can_read = r.can_read(file, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.debug("%s: %s [%s]", e.__class__.__name__, e, r.__name__)
                continue

            if can_read:
                logger.debug("reading file with %s", r.__name__)
                root = r(file)
                root.read(**kwargs)
                root.read_only = True
                return root

    msg = f"No Reader exists to read {file!r}"
    raise OSError(msg)


_readers: list[type[Reader]] = []
