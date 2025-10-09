# noqa: D100
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .node import Group
from .utils import get_basename, is_file_readable

if TYPE_CHECKING:
    import sys
    from typing import Any

    from .types import PathLike, ReadLike, WriteLike

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

    def __init__(
        self,
        file: PathLike | ReadLike | WriteLike | None,
        **metadata: Any,
    ) -> None:
        """The root [Group][msl.io.node.Group].

        Args:
            file: The file object to associate with the [Root][msl.io.base.Root].
            metadata: All keyword arguments are used as [Metadata][msl.io.metadata.Metadata].
        """
        super().__init__(name="/", parent=None, read_only=False, **metadata)
        self._root_file: PathLike | ReadLike | WriteLike | None = file

    def __repr__(self) -> str:
        """Returns the string representation of the Root."""
        b = get_basename(self._root_file) if self._root_file is not None else "None"
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        groups = "group" if g == 1 else "groups"
        datasets = "dataset" if d == 1 else "datasets"
        return f"<{self.__class__.__name__} {b!r} ({g} {groups}, {d} {datasets}, {m} metadata)>"

    def tree(self, *, indent: int = 2) -> str:
        """Returns a string representation of the [tree structure](https://en.wikipedia.org/wiki/Tree_structure){:target="_blank"}.

        Shows all [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s that are in [Root][msl.io.base.Root].

        Args:
            indent: The amount of indentation to add for each recursive level.

        Returns:
            The [tree structure](https://en.wikipedia.org/wiki/Tree_structure){:target="_blank"}.
        """
        return repr(self) + "\n" + "\n".join(" " * (indent * k.count("/")) + repr(v) for k, v in sorted(self.items()))


class Writer(Root, ABC):
    """Abstract base class for a [Writer][msl-io-writers]."""

    def __init__(self, file: PathLike | WriteLike | None = None, **metadata: Any) -> None:
        """Abstract base class for a [Writer][msl-io-writers].

        Args:
            file: The file to write the data to. Can also be specified in the [write][msl.io.base.Writer.write] method.
            metadata: All keyword arguments are used as [Metadata][msl.io.metadata.Metadata].
        """
        super().__init__(file, **metadata)
        self._file: PathLike | WriteLike | None = file
        self._context_kwargs: dict[str, Any] = {}

    @property
    def file(self) -> PathLike | WriteLike | None:
        """[PathLike][msl.io.types.PathLike] | [WriteLike][msl.io.types.WriteLike] | None &mdash; The file object associated with the [Writer][msl.io.base.Writer]."""  # noqa: E501
        return self._file

    def set_root(self, root: Group) -> None:
        """Set a new [Root][msl.io.base.Root] for the [Writer][msl.io.base.Writer].

        !!! info
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
        """Update the keyword arguments when used as a [context manager][with]{:target="_blank"}.

        When a [Writer][msl.io.base.Writer] is used as a [context manager][with]{:target="_blank"}
        the [write][msl.io.base.Writer.write] method is automatically called when exiting the
        [context manager][with]{:target="_blank"}. You can specify the keyword arguments
        that will be passed to the [write][msl.io.base.Writer.write] method by calling
        [update_context_kwargs][msl.io.base.Writer.update_context_kwargs] with the appropriate
        keyword arguments before the [context manager][with]{:target="_blank"} exits. You may
        call this method multiple times.
        """
        self._context_kwargs.update(**kwargs)

    @abstractmethod
    def write(self, file: PathLike | WriteLike | None = None, root: Group | None = None, **kwargs: Any) -> None:
        """Write to a file.

        !!! warning "You must override this method."

        Args:
            file: The file to write the `root` to. If `None` then uses the `file` value
                that was specified when the [Writer][msl.io.base.Writer] was instantiated.
            root: Write the `root` object in the file format of this [Writer][msl.io.base.Writer].
                This argument is useful when converting between different file formats.
            kwargs: Keyword arguments to use when writing the file.
        """

    def save(
        self,
        file: PathLike | WriteLike | None = None,
        *,
        root: Group | None = None,
        **kwargs: Any,
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

    def __init__(self, file: ReadLike | str) -> None:
        """Abstract base class for a [Reader][msl-io-readers].

        Args:
            file: The file to read.
        """
        super().__init__(file)
        self._file: ReadLike | str = file

    def __init_subclass__(cls) -> None:
        """This method is called whenever the Reader is sub-classed."""
        logger.debug("msl-io registered %r", cls)
        _readers.append(cls)

    @staticmethod
    @abstractmethod
    def can_read(file: ReadLike | str, **kwargs: Any) -> bool:
        """Whether this [Reader][msl.io.base.Reader] can read the file specified by `file`.

        !!! warning "You must override this method."

        Args:
            file: The file to check whether the [Reader][msl.io.base.Reader] can read it.
            kwargs: Keyword arguments that the [Reader][msl.io.base.Reader] class may need
                when checking if it can read the `file`.

        Returns:
            Either `True` (can read) or `False` (cannot read).
        """

    @property
    def file(self) -> ReadLike | str:
        """[ReadLike][msl.io.types.ReadLike] | [str][] &mdash; The file object associated with the [Reader][msl.io.base.Reader]."""  # noqa: E501
        return self._file

    @abstractmethod
    def read(self, **kwargs: Any) -> None:
        """Read the file.

        The file to read can be accessed by the [file][msl.io.base.Reader.file] property.

        !!! warning "You must override this method."

        Args:
            kwargs: Keyword arguments that the [Reader][msl.io.base.Reader] class may need
                when reading the file.
        """


def read(file: PathLike | ReadLike, **kwargs: Any) -> Reader:
    """Read a file that has a [Reader][msl-io-readers] implemented.

    !!! example "See the [Overview][read-a-file] for an example."

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
