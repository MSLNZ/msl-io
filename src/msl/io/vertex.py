"""Vertex object types."""
from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from datetime import datetime
from logging import Logger
from typing import TYPE_CHECKING, Any

import numpy as np

from .freezable import FreezableMap
from .metadata import Metadata

if TYPE_CHECKING:
    from collections.abc import Buffer, Iterator
    from typing import Literal, SupportsIndex

    from numpy.typing import ArrayLike, DTypeLike, NDArray

    from ._types import ShapeLike, ToIndices
    from .group import Group


class Vertex(FreezableMap["Vertex"]):
    """A vertex in a tree."""

    def __init__(self, *, name: str, parent: Group | None, read_only: bool, **metadata: Any) -> None:
        """A vertex in a tree.

        Args:
            name: The name of the vertex.
            parent: The parent of the vertex.
            read_only: Whether the vertex is initialised in read-only mode.
            metadata: Key-value pairs are used to create the [Metadata][msl.io.metadata.Metadata] for the vertex.
        """
        super().__init__(read_only=read_only)

        if not name:
            msg = "The vertex name cannot be an empty string"
            raise ValueError(msg)

        if parent is not None:
            if "/" in name:
                msg = "The vertex name cannot contain the '/' character"
                raise ValueError(msg)

            # use a path name similar to a UNIX file system
            name = f"{parent.name}{name}" if parent.name.endswith("/") else f"{parent.name}/{name}"

            # notify all ancestors that this vertex was created
            i = 0
            ancestor: Group | None = parent
            name_split = name.split("/")
            while ancestor is not None:
                i += 1
                key = "/" + "/".join(name_split[-i:])
                if key in ancestor._mapping:  # noqa: SLF001
                    msg = f"The name of this vertex, {key!r}, is not unique"
                    raise ValueError(msg)
                ancestor._mapping[key] = self  # noqa: SLF001
                ancestor = ancestor._parent  # noqa: SLF001

        self._name: str = name
        self._parent: Group | None = parent
        self._metadata: Metadata = Metadata(read_only=read_only, vertex_name=name, **metadata)

    def __delitem__(self, item: str) -> None:  # noqa: C901
        """Maybe delete a vertex, if the vertex is not in read-only mode."""
        self._raise_if_read_only()
        if item and item[0] != "/":
            item = "/" + item

        try:
            popped = self._mapping.pop(item)
        except KeyError:
            msg = f"{item!r} is not in {self!r}"
            raise KeyError(msg) from None
        else:
            # use recursion to delete the reference to
            # `popped` from the head of this Vertex
            head, tail = os.path.split(item)
            if head != "/":
                assert self[head].pop(tail) is popped  # noqa: S101

            def notify_ancestors(obj: Vertex) -> None:
                # delete all references to `obj` from the ancestors of this Vertex
                ancestor = self._parent
                while ancestor is not None:
                    for k, v in list(ancestor.items()):
                        if obj is v:
                            del ancestor._mapping[k]  # noqa: SLF001
                    ancestor = ancestor._parent  # noqa: SLF001

            notify_ancestors(popped)

            # delete all descendant of this Vertex
            # (this is necessary if the popped item is a Group)
            for name, vertex in list(self.items()):
                if vertex.name.startswith(popped.name):
                    vertex = self._mapping.pop(name)  # noqa: PLW2901
                    notify_ancestors(vertex)

    @property
    def read_only(self) -> bool:
        """[bool][] &mdash; Whether this [Vertex][msl.io.vertex.Vertex] is in read-only mode.

        Setting this value will also update all sub-[Group][msl.io.group.Group]s
        and sub-[Dataset][msl.io.dataset.Dataset]s to be in the same mode.
        """
        return self._read_only

    @read_only.setter
    def read_only(self, value: bool) -> None:
        val = bool(value)

        self._read_only: bool = val
        self._metadata.read_only = val

        # update all descendants of this vertex
        for obj in self._mapping.values():
            obj.read_only = val

    @property
    def name(self) -> str:
        """[str][] &mdash; The name of this [Vertex][msl.io.vertex.Vertex]."""
        return self._name

    @property
    def parent(self) -> Group | None:
        """[Group][msl.io.group.Group] | None &mdash; The parent of this [Vertex][msl.io.vertex.Vertex]."""
        return self._parent

    @property
    def metadata(self) -> Metadata:
        """[Metadata][msl.io.metadata.Metadata] &mdash; The metadata for this [Vertex][msl.io.vertex.Vertex]."""
        return self._metadata

    def add_metadata(self, **metadata: Any) -> None:
        """Add metadata to the vertex.

        Args:
            metadata: Key-value pairs to add to the [Metadata][msl.io.metadata.Metadata] for this
                [Vertex][msl.io.vertex.Vertex].
        """
        self._metadata.update(**metadata)


class Dataset(Vertex, np.lib.mixins.NDArrayOperatorsMixin, Sequence[Any]):
    """A `Dataset` functions as a [numpy.ndarray][] with [Metadata][msl.io.metadata.Metadata]."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        name: str,
        parent: Group | None,
        read_only: bool,
        shape: ShapeLike = (0,),
        dtype: DTypeLike = float,
        buffer: Buffer | None = None,
        offset: SupportsIndex = 0,
        strides: ShapeLike | None = None,
        order: Literal["K", "A", "C", "F"] | None = None,
        data: ArrayLike | None = None,
        **metadata: Any,
    ) -> None:
        """A `Dataset` functions as a [numpy.ndarray][] with [Metadata][msl.io.metadata.Metadata].

        !!! attention
            Do not instantiate directly. Create a new [Dataset][] using the
            [create_dataset][msl.io.group.Group.create_dataset] method.

        Args:
            name: A name to associate with this [Dataset][].
            parent: The parent [Group][msl.io.group.Group] to the [Dataset][].
            read_only: Whether the [Dataset][] is initialised in read-only mode.
            shape: See [numpy.ndarray][]. Only used if `data` is `None`.
            dtype: See [numpy.ndarray][]. Only used if `data` is `None` or if
                `data` is not a [numpy.ndarray][] instance.
            buffer: See [numpy.ndarray][]. Only used if `data` is `None`.
            offset: See [numpy.ndarray][]. Only used if `data` is `None`.
            strides: See [numpy.ndarray][]. Only used if `data` is `None`.
            order: See [numpy.ndarray][]. Only used if `data` is `None` or if
                `data` is not a [numpy.ndarray][] instance.
            data: If not `None`, it must be either a [numpy.ndarray][] or
                an array-like object which will be passed to [numpy.asarray][],
                as well as `dtype` and `order`, to be used as the underlying data.
            metadata: All other key-value pairs will be used as
                [Metadata][msl.io.metadata.Metadata] for this [Dataset][].
        """
        super().__init__(name=name, parent=parent, read_only=read_only, **metadata)

        self._data: NDArray[Any]
        if data is None:
            self._data = np.ndarray(shape, dtype=dtype, buffer=buffer, offset=offset, strides=strides, order=order)
        elif isinstance(data, np.ndarray):
            self._data = data
        else:
            self._data = np.asarray(data, dtype=dtype, order=order)

        self.read_only = read_only

    def __array_ufunc__(
        self, ufunc: np.ufunc, method: str, *inputs: Any, **kwargs: Any
    ) -> None | Dataset | tuple[Dataset, ...]:
        """Handles numpy functions and Python operators."""
        # See https://numpy.org/doc/stable/reference/generated/numpy.lib.mixins.NDArrayOperatorsMixin.html
        if method == "at":
            return None

        metadata: dict[str, Any] = {}
        names: list[str] = []
        for item in inputs:
            if isinstance(item, Dataset):
                metadata.update(item.metadata.copy())
                names.append(item.name)
        name = f"{ufunc.__name__}({','.join(names)})"

        out = kwargs.get("out", ())
        if out:
            kwargs["out"] = tuple(o.data if isinstance(o, Dataset) else o for o in out)

        inputs = tuple(i.data if isinstance(i, Dataset) else i for i in inputs)
        result: NDArray[Any] | tuple[NDArray[Any], ...] = getattr(ufunc, method)(*inputs, **kwargs)

        if isinstance(result, tuple):
            return tuple(
                type(self)(name=name, parent=None, read_only=self._read_only, data=r, **metadata) for r in result
            )
        return type(self)(name=name, parent=None, read_only=self._read_only, data=result, **metadata)

    def __getattr__(self, item: str | ToIndices) -> Any:
        """Get an attribute of the numpy array."""
        try:
            return getattr(self._data, item)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
        except AttributeError:
            try:
                return self._data[item]
            except (IndexError, ValueError):
                pass
            raise

    def __getitem__(self, key: str | ToIndices | NDArray[Any]) -> NDArray[Any]:  # type: ignore[override] # pyright: ignore[reportIncompatibleMethodOverride]
        """Get a value from the numpy array."""
        return self._data[key]

    def __iter__(self) -> Iterator[Any]:
        """Returns an iterator over the items in the numpy array."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return the length of the numpy array."""
        try:
            return len(self._data)
        except TypeError:  # the ndarray is a scalar
            return self._data.size

    def __repr__(self) -> str:
        """Returns the string representation of the Dataset instance."""
        return (
            f"<{self.__class__.__name__} "
            f"{self._name!r} "
            f"shape={self._data.shape} "
            f"dtype={self._data.dtype.str!r} "
            f"({len(self.metadata)} metadata)>"
        )

    def __setitem__(self, key: str | ToIndices | NDArray[Any], value: ArrayLike) -> None:  # type: ignore[override] # pyright: ignore[reportIncompatibleMethodOverride]
        """Set a value for the numpy array."""
        self._data[key] = value

    def __str__(self) -> str:
        """Returns the string representation of the numpy array."""
        return repr(self._data)

    def copy(self, read_only: bool | None = None) -> Dataset:
        """Create a copy of this [Dataset][].

        Args:
            read_only: Whether the copy should be created in read-only mode. If `None`,
                creates a copy using the mode for the [Dataset][] that is being copied.

        Returns:
            A copy of this [Dataset][].
        """
        return Dataset(
            name=self._name,
            parent=self._parent,
            read_only=self._read_only if read_only is None else read_only,
            data=self._data.copy(),
            **self._metadata.copy(),
        )

    @property
    def data(self) -> NDArray[Any]:
        """[numpy.ndarray][] &mdash; The data of the [Dataset][].

        !!! note
            You do not have to call this attribute to access the underlying [numpy.ndarray][].
            You can directly call any [numpy.ndarray][] attribute from the [Dataset][] instance.
            For example,

            <!-- invisible-code-block: pycon
            >>> from msl.io import JSONWriter
            >>> root = JSONWriter()
            >>> dataset = root.create_dataset("my_data", data=[[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]])

            -->

           ```pycon
           >>> dataset
           <Dataset '/my_data' shape=(4, 3) dtype='<f8' (0 metadata)>
           >>> dataset.data
           array([[ 0.,  1.,  2.],
                   [ 3.,  4.,  5.],
                   [ 6.,  7.,  8.],
                   [ 9., 10., 11.]])
           >>> dataset.size
           12
           >>> dataset.tolist()
           [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0], [6.0, 7.0, 8.0], [9.0, 10.0, 11.0]]
           >>> dataset.mean(axis=0)
           array([4.5, 5.5, 6.5])
           >>> dataset[::2]
           array([[0., 1., 2.],
                   [6., 7., 8.]])

           ```
        """
        return self._data

    @property
    def read_only(self) -> bool:
        """[bool][] &mdash; Whether the [Dataset][] is in read-only mode.

        This is equivalent to setting the `WRITEABLE` property in [numpy.ndarray.setflags][].
        """
        return not self._data.flags.writeable

    @read_only.setter
    def read_only(self, value: bool) -> None:
        val = bool(value)
        self._metadata.read_only = val
        self._data.setflags(write=not val)


class DatasetLogging(Dataset):
    """A [Dataset][msl.io.vertex.Dataset] that handles [logging][] records."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        name: str,
        parent: Group | None,
        attributes: Sequence[str],
        level: str | int = logging.NOTSET,
        logger: logging.Logger | None = None,
        date_fmt: str | None = None,
        **kwargs: Any,
    ) -> None:
        """A [Dataset][msl.io.vertex.Dataset] that handles [logging][] records.

        !!! attention
            Do not instantiate directly. Create a new [DatasetLogging][] using
            [create_dataset_logging][msl.io.group.Group.create_dataset_logging].

        Args:
            name: A name to associate with the [Dataset][msl.io.vertex.Dataset].
            parent: The parent to the `DatasetLogging`.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.vertex.Dataset] for each [logging record][log-record].
            level: The [logging level][levels] to use.
            logger: The [Logger][logging.Logger] that this `DatasetLogging` instance
                will be added to. If `None`, it is added to the `root` [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] (only if
                _asctime_ is included as one of the `attributes`).
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.vertex.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.vertex.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.vertex.Dataset] is equal to the number of [logging records][log-record]
                that were added to it. However, this behaviour can decrease performance if many
                [logging records][log-record] are added often because a copy of the data in the
                [Dataset][msl.io.vertex.Dataset] is created for each :ref:`logging record <log-record>`
                that is added. You can improve performance by specifying an initial size of the
                [Dataset][msl.io.vertex.Dataset] by including a `shape` or a `size` keyword argument.
                This will also automatically allocate more memory that is proportional to the size of the
                [Dataset][msl.io.vertex.Dataset], if the size of the
                [Dataset][msl.io.vertex.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.vertex.DatasetLogging.remove_empty_rows] before
                writing `DatasetLogging` to a file or interacting with the data in `DatasetLogging` to
                remove the extra _empty_ rows that were created.
        """
        if not attributes:
            msg = "Must specify logging attributes"
            raise ValueError(msg)

        if not all(isinstance(a, str) for a in attributes):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Must specify attribute names as strings, got: {attributes}"
            raise ValueError(msg)

        self._logger: logging.Logger | None = None
        self._attributes: tuple[str, ...] = tuple(attributes)
        self._uses_asctime: bool = "asctime" in attributes
        self._date_fmt: str = date_fmt or "%Y-%m-%dT%H:%M:%S.%f"

        _level: int = getattr(logging, level) if isinstance(level, str) else int(level)

        # these 3 keys in the metadata are used to distinguish a DatasetLogging
        # object from a regular Dataset object
        kwargs["logging_level"] = _level
        kwargs["logging_level_name"] = logging.getLevelName(_level)
        kwargs["logging_date_format"] = date_fmt

        self._auto_resize: bool = "size" in kwargs or "shape" in kwargs
        if self._auto_resize:
            if "size" in kwargs:
                kwargs["shape"] = (kwargs.pop("size"),)
            elif isinstance(kwargs["shape"], int):
                kwargs["shape"] = (kwargs["shape"],)

            shape = kwargs["shape"]
            if len(shape) != 1:
                msg = f"Invalid shape {shape}, the number of dimensions must be 1"
                raise ValueError(msg)
            if shape[0] < 0:
                msg = f"Invalid shape {shape}"
                raise ValueError(msg)

        self._dtype: np.dtype = np.dtype([(a, object) for a in attributes])
        super().__init__(name=name, parent=parent, read_only=False, dtype=self._dtype, **kwargs)

        self._index: np.intp = np.count_nonzero(self._data)
        if self._auto_resize and self._data.shape < kwargs["shape"]:
            self._resize(new_allocated=kwargs["shape"][0])

        self._handler: logging.Handler = logging.Handler(level=_level)
        self._handler.set_name(self.name)
        self._handler.emit = self._emit  # type: ignore[method-assign]
        self.set_logger(logger or logging.getLogger())

    def _emit(self, record: logging.LogRecord) -> None:
        """Overrides the `logging.Handler.emit` method."""
        record.message = record.getMessage()
        if self._uses_asctime:
            record.asctime = datetime.fromtimestamp(record.created).strftime(self._date_fmt)  # noqa: DTZ006
        latest = tuple(record.__dict__[a] for a in self._attributes)
        row = np.asarray(latest, dtype=self._dtype)
        if self._auto_resize:
            if self._index >= self._data.size:
                self._resize()
            self._data[self._index] = row
            self._index += 1
        else:
            self._data = np.append(self._data, row)

    def _resize(self, new_allocated: int | None = None) -> None:
        # Over-allocates proportional to the size of the ndarray, making room
        # for additional growth. This follows the over-allocating procedure that
        # Python uses when appending to a list object, see `list_resize` in
        # https://github.com/python/cpython/blob/master/Objects/listobject.c
        if new_allocated is None:
            new_size = self._data.size + 1
            new_allocated = new_size + (new_size >> 3) + (3 if new_size < 9 else 6)  # noqa: PLR2004

        # don't use self._data.resize() because that fills the newly-created rows
        # with 0 and want to fill the new rows with None to be explicit that the
        # new rows are not associated with logging records
        array = np.empty((new_allocated,), dtype=self._dtype)
        array[: self._data.size] = self._data
        self._data = array

    def add_filter(self, log_filter: logging.Filter) -> None:
        """Add a logging filter.

        Args:
            log_filter: The logging [Filter][logging.Filter] to add to the [Handler][logging.Handler]
        """
        self._handler.addFilter(log_filter)

    @property
    def attributes(self) -> tuple[str, ...]:
        """[tuple][] of [str][] &mdash; The [attribute names][logrecord-attributes] that are logged."""
        return self._attributes

    @property
    def date_fmt(self) -> str:
        """[str][] &mdash; The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]."""
        return self._date_fmt

    @property
    def level(self) -> int:
        """[int][] &mdash; The [logging level][levels] that is used."""
        return self._handler.level

    @level.setter
    def level(self, value: int) -> None:
        self._handler.setLevel(value)

    @property
    def logger(self) -> Logger | None:
        """[Logger][logging.Logger] | `None` &mdash; The [Logger][logging.Logger] for this `DatasetLogging`."""
        return self._logger

    def remove_empty_rows(self) -> None:
        """Remove empty rows from the [Dataset][msl.io.vertex.Dataset].

        If the [DatasetLogging][msl.io.vertex.DatasetLogging] object was initialized with a `shape` or a `size`
        keyword argument then the size of the [Dataset][msl.io.vertex.Dataset] is always &ge; to the number of
        [logging records][log-record] that were added to it. Calling this method will remove the rows in the
        [Dataset][msl.io.vertex.Dataset] that were not from a [logging record][log-record].
        """
        assert self._dtype.names is not None  # noqa: S101

        # don't use "is not None" since this does not work as expected
        self._data: NDArray[Any] = self._data[self._data[self._dtype.names[0]] != None]  # noqa: E711

    def remove_filter(self, log_filter: logging.Filter) -> None:
        """Remove a logging filter.

        Args:
            log_filter: The logging [Filter][logging.Filter] to remove from the [Handler][logging.Handler]
        """
        self._handler.removeFilter(log_filter)

    def remove_handler(self) -> None:
        """Remove this class's [Handler][logging.Handler] from the associated [Logger][logging.Logger].

        After calling this method [logging records][log-record] are no longer added
        to the [Dataset][msl.io.vertex.Dataset].
        """
        if self._logger is not None:
            self._logger.removeHandler(self._handler)

    def set_logger(self, logger: logging.Logger) -> None:
        """Add this class's [Handler][logging.Handler] to a [Logger][logging.Logger].

        Args:
            logger: The [Logger][logging.Logger] to add this class's [Handler][logging.Handler] to.
        """
        level = self._handler.level
        if logger.level == 0 or logger.level > level:
            logger.setLevel(level)

        self.remove_handler()
        logger.addHandler(self._handler)
        self._logger = logger
