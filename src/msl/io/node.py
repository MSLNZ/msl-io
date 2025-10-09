"""Node objects in the hierarchical tree."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

import numpy as np

from .freezable import FreezableMap
from .metadata import Metadata

if TYPE_CHECKING:
    from collections.abc import Iterator
    from logging import Logger
    from typing import Literal, SupportsIndex

    from numpy.typing import ArrayLike, DTypeLike, NDArray

    from .types import Buffer, ShapeLike, ToIndices


class Dataset(np.lib.mixins.NDArrayOperatorsMixin, Sequence[Any]):  # noqa: PLW1641
    """A *Dataset* functions as a numpy [ndarray][numpy.ndarray] with [Metadata][msl.io.metadata.Metadata]."""

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
        """A *Dataset* functions as a numpy [ndarray][numpy.ndarray] with [Metadata][msl.io.metadata.Metadata].

        !!! warning
            Do not instantiate directly. Create a new [Dataset][msl.io.node.Dataset] using the
            [create_dataset][msl.io.node.Group.create_dataset] method.

        Args:
            name: A name to associate with this [Dataset][msl.io.node.Dataset].
            parent: The parent [Group][msl.io.node.Group] to the [Dataset][msl.io.node.Dataset].
            read_only: Whether the [Dataset][msl.io.node.Dataset] is initialised in read-only mode.
            shape: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None`.
            dtype: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None` or if
                `data` is not a numpy [ndarray][numpy.ndarray] instance.
            buffer: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None`.
            offset: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None`.
            strides: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None`.
            order: See numpy [ndarray][numpy.ndarray]. Only used if `data` is `None` or if
                `data` is not a numpy [ndarray][numpy.ndarray] instance.
            data: If not `None`, it must be either a numpy [ndarray][numpy.ndarray] or
                an array-like object which will be passed to [asarray][numpy.asarray],
                as well as `dtype` and `order`, to be used as the underlying data.
            metadata: All other keyword arguments are used as
                [Metadata][msl.io.metadata.Metadata] for this [Dataset][msl.io.node.Dataset].
        """
        name = _unix_name(name, parent)
        self._name: str = name
        self._parent: Group | None = parent
        self._metadata: Metadata = Metadata(read_only=read_only, node_name=name, **metadata)

        self._data: NDArray[Any]
        if data is None:
            self._data = np.ndarray(shape, dtype=dtype, buffer=buffer, offset=offset, strides=strides, order=order)
        elif isinstance(data, np.ndarray):
            self._data = data
        elif isinstance(data, Dataset):
            self._data = data.data
        else:
            self._data = np.asarray(data, dtype=dtype, order=order)

        self.read_only = read_only
        _notify_created(self, parent)

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
                type(self)(name=name, parent=None, read_only=self.read_only, data=r, **metadata) for r in result
            )
        return type(self)(name=name, parent=None, read_only=self.read_only, data=result, **metadata)

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

    def __setitem__(self, key: str | ToIndices | NDArray[Any], value: ArrayLike) -> None:
        """Set a value for the numpy array."""
        self._data[key] = value

    def __str__(self) -> str:
        """Returns the string representation of the numpy array."""
        return repr(self._data)

    def __eq__(self, other: object) -> bool:
        """Comparison with another Dataset instance."""
        # Do not implement __hash__ (see https://docs.python.org/3/reference/datamodel.html#object.__hash__)
        #
        # "If a class defines mutable objects and implements an __eq__() method, it should not implement __hash__(),
        # since the implementation of hashable collections requires that a key's hash value is immutable (if the
        # object's hash value changes, it will be in the wrong hash bucket)."
        if not isinstance(other, Dataset):
            return False
        if self._name != other._name:
            return False
        if self._metadata != other._metadata:
            return False
        # self.name derives from self.parent so we don't need to check equality of self.parent.name
        return np.array_equal(self._data, other._data)

    def __ne__(self, other: object) -> bool:
        """Comparison with another Dataset instance."""
        # Must implement __ne__ to override NDArrayOperatorsMixin.__ne__ since the default behaviour
        # of delegating to __eq__ and inverting the result does not happen without overriding __ne__
        return not self == other

    @property
    def name(self) -> str:
        """[str][] &mdash; The name of this [Dataset][msl.io.node.Dataset]."""
        return self._name

    @property
    def parent(self) -> Group | None:
        """[Group][msl.io.node.Group] | None &mdash; The parent of this [Dataset][msl.io.node.Dataset]."""
        return self._parent

    @property
    def metadata(self) -> Metadata:
        """[Metadata][msl.io.metadata.Metadata] &mdash; The metadata for this [Dataset][msl.io.node.Dataset]."""
        return self._metadata

    def add_metadata(self, **metadata: Any) -> None:
        """Add metadata to the [Dataset][msl.io.node.Dataset].

        Args:
            metadata: Key-value pairs to add to the [Metadata][msl.io.metadata.Metadata] for this
                [Dataset][msl.io.node.Dataset].
        """
        self._metadata.update(**metadata)

    def copy(self, *, read_only: bool | None = None) -> Dataset:
        """Create a copy of this [Dataset][msl.io.node.Dataset].

        Args:
            read_only: Whether the copy should be created in read-only mode. If `None`,
                creates a copy using the mode for the [Dataset][msl.io.node.Dataset] that is being copied.

        Returns:
            A copy of this [Dataset][msl.io.node.Dataset].
        """
        return Dataset(
            name=self._name,
            parent=self._parent,
            read_only=self.read_only if read_only is None else read_only,
            data=self._data.copy(),
            **self._metadata.copy(),
        )

    @property
    def data(self) -> NDArray[Any]:
        """[ndarray][numpy.ndarray] &mdash; The data of the [Dataset][msl.io.node.Dataset].

        <!-- invisible-code-block: pycon
        >>> from msl.io import JSONWriter
        >>> root = JSONWriter()
        >>> dataset = root.create_dataset("my_data", data=[[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]])

        -->

        !!! tip
            You do not have to call this attribute to access the underlying numpy [ndarray][numpy.ndarray].
            You can directly call any [ndarray][numpy.ndarray] attribute from the [Dataset][msl.io.node.Dataset]
            instance.

            For example,

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
        """[bool][] &mdash; Whether the [Dataset][msl.io.node.Dataset] is in read-only mode.

        This is equivalent to setting the `WRITEABLE` property in [numpy.ndarray.setflags][]{:target="_blank"}.
        """
        return not self._data.flags.writeable

    @read_only.setter
    def read_only(self, value: bool) -> None:
        val = bool(value)
        self._metadata.read_only = val
        self._data.setflags(write=not val)


class DatasetLogging(Dataset):
    """A [Dataset][msl.io.node.Dataset] that handles [logging][]{:target="_blank"} records."""

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
        """A [Dataset][msl.io.node.Dataset] that handles [logging][]{:target="_blank"} records.

        !!! warning
            Do not instantiate directly. Create a new [DatasetLogging][msl.io.node.DatasetLogging] using
            [create_dataset_logging][msl.io.node.Group.create_dataset_logging].

        Args:
            name: A name to associate with the [Dataset][msl.io.node.Dataset].
            parent: The parent to the `DatasetLogging`.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.node.Dataset] for each [logging record][log-record].
            level: The [logging level][levels] to use.
            logger: The [Logger][logging.Logger] that this `DatasetLogging` instance
                will be associated with. If `None`, it is associated with the _root_ [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] (only if
                _asctime_ is included as one of the `attributes`).
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.node.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.node.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.node.Dataset] is equal to the number of [logging records][log-record]
                that were added to it. However, this behaviour can decrease performance if many
                [logging records][log-record] are added often because a copy of the data in the
                [Dataset][msl.io.node.Dataset] is created for each [logging record][log-record]
                that is added. You can improve performance by specifying an initial size of the
                [Dataset][msl.io.node.Dataset] by including a `shape` or a `size` keyword argument.
                This will also automatically allocate more memory that is proportional to the size of the
                [Dataset][msl.io.node.Dataset], if the size of the
                [Dataset][msl.io.node.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.node.DatasetLogging.remove_empty_rows] before
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

        self._dtype: np.dtype[np.object_ | np.void] = np.dtype([(a, object) for a in attributes])
        super().__init__(name=name, parent=parent, read_only=False, dtype=self._dtype, **kwargs)

        self._index: int | np.intp = np.count_nonzero(self._data)
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
        """[tuple][][[str][], ...] &mdash; The [attribute names][logrecord-attributes] that are logged."""
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
        """Remove empty rows from the [Dataset][msl.io.node.Dataset].

        If the [DatasetLogging][msl.io.node.DatasetLogging] object was initialized with a `shape` or a `size`
        keyword argument then the size of the [Dataset][msl.io.node.Dataset] is always greater than or equal to
        the number of [logging records][log-record] that were added to it. Calling this method will remove the
        rows in the [Dataset][msl.io.node.Dataset] that were not from a [logging record][log-record].
        """
        assert self._dtype.names is not None  # noqa: S101

        # don't use "is not None" since this does not work as expected
        self._data: NDArray[Any] = self._data[self._data[self._dtype.names[0]] != None]  # noqa: E711

    def remove_filter(self, log_filter: logging.Filter) -> None:
        """Remove a logging filter.

        Args:
            log_filter: The logging [Filter][logging.Filter] to remove from the [Handler][logging.Handler].
        """
        self._handler.removeFilter(log_filter)

    def remove_handler(self) -> None:
        """Remove this class's [Handler][logging.Handler] from the associated [Logger][logging.Logger].

        After calling this method [logging records][log-record] are no longer added
        to the [Dataset][msl.io.node.Dataset].
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


class Group(FreezableMap["Dataset | Group"]):  # noqa: PLW1641
    """A [Group][msl.io.node.Group] can contain sub-[Group][msl.io.node.Group]s and/or [Dataset][msl.io.node.Dataset]s."""  # noqa: E501

    def __init__(self, *, name: str, parent: Group | None, read_only: bool, **metadata: Any) -> None:
        """A [Group][msl.io.node.Group] can contain sub-[Group][msl.io.node.Group]s and/or [Dataset][msl.io.node.Dataset]s.

        !!! warning
            Do not instantiate directly. Create a new [Group][msl.io.node.Group] using
            [create_group][msl.io.node.Group.create_group].

        Args:
            name: The name of this [Group][msl.io.node.Group]. Uses a naming convention analogous to UNIX
                file systems where each [Group][msl.io.node.Group] can be thought
                of as a directory and where every subdirectory is separated from its
                parent directory by the `/` character.
            parent: The parent to this [Group][msl.io.node.Group].
            read_only: Whether the [Group][msl.io.node.Group] is initialised in read-only mode.
            metadata: All additional keyword arguments are used to create the
                [Metadata][msl.io.metadata.Metadata] for this [Group][msl.io.node.Group].
        """  # noqa: E501
        name = _unix_name(name, parent)
        self._name: str = name
        self._parent: Group | None = parent
        self._metadata: Metadata = Metadata(read_only=read_only, node_name=name, **metadata)
        _notify_created(self, parent)
        super().__init__(read_only=read_only)

    def __delitem__(self, item: str) -> None:  # noqa: C901
        """Maybe delete a Group, if the Group is not in read-only mode."""
        self._raise_if_read_only()
        if item and item[0] != "/":
            item = f"/{item}"

        try:
            popped = self._mapping.pop(item)
        except KeyError:
            msg = f"{item!r} is not in {self!r}"
            raise KeyError(msg) from None
        else:
            # use recursion to delete the reference to
            # `popped` from the head of this Group
            head, tail = os.path.split(item)
            if head != "/":
                assert self[head].pop(tail) is popped  # noqa: S101

            def notify_ancestors(node: Dataset | Group) -> None:
                # delete all references to the node from the ancestors of this Group
                ancestor = self._parent
                while ancestor is not None:
                    for k, v in list(ancestor.items()):
                        if node is v:
                            del ancestor._mapping[k]  # noqa: SLF001
                    ancestor = ancestor._parent  # noqa: SLF001

            notify_ancestors(popped)

            # delete all descendant of this Group
            for name, node in list(self.items()):
                if node.name.startswith(popped.name):
                    node = self._mapping.pop(name)  # noqa: PLW2901
                    notify_ancestors(node)

    def __repr__(self) -> str:
        """Returns the string representation of the `Group`."""
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        groups = "group" if g == 1 else "groups"
        datasets = "dataset" if d == 1 else "datasets"
        return f"<Group {self._name!r} ({g} {groups}, {d} {datasets}, {m} metadata)>"

    def __getitem__(self, item: str) -> Dataset | Group:
        """Get an item from the `Group`."""
        if item and item[0] != "/":
            item = f"/{item}"

        try:
            return self._mapping[item]
        except KeyError:
            msg = f"{item!r} is not in {self!r}"
            raise KeyError(msg) from None

    def __getattr__(self, item: str) -> Dataset | Group:
        """Get an item from the `Group`."""
        try:
            return self.__getitem__(f"/{item}")
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def __delattr__(self, item: str) -> None:
        """Delete and item from the `Group`."""
        try:
            return self.__delitem__(f"/{item}")
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def __eq__(self, other: object) -> bool:  # noqa: PLR0911
        """Comparison with another Group instance."""
        # Do not implement __hash__ (see https://docs.python.org/3/reference/datamodel.html#object.__hash__)
        #
        # "If a class defines mutable objects and implements an __eq__() method, it should not implement __hash__(),
        # since the implementation of hashable collections requires that a key's hash value is immutable (if the
        # object's hash value changes, it will be in the wrong hash bucket)."
        if not isinstance(other, Group):
            return False
        if self._name != other._name:
            return False
        if self._metadata != other._metadata:
            return False
        if len(self) != len(other):
            return False
        for k1, v1 in self.items():
            if k1 not in other:
                return False
            if v1 != other[k1]:
                return False
        # self.name derives from self.parent so we don't need to check equality of self.parent.name
        return True

    @property
    def name(self) -> str:
        """[str][] &mdash; The name of this [Group][msl.io.node.Group]."""
        return self._name

    @property
    def parent(self) -> Group | None:
        """[Group][msl.io.node.Group] | None &mdash; The parent of this [Group][msl.io.node.Group]."""
        return self._parent

    @property
    def metadata(self) -> Metadata:
        """[Metadata][msl.io.metadata.Metadata] &mdash; The metadata for this [Group][msl.io.node.Group]."""
        return self._metadata

    def add_metadata(self, **metadata: Any) -> None:
        """Add metadata to the [Group][msl.io.node.Group].

        Args:
            metadata: Key-value pairs to add to the [Metadata][msl.io.metadata.Metadata] for this
                [Group][msl.io.node.Group].
        """
        self._metadata.update(**metadata)

    @property
    def read_only(self) -> bool:
        """[bool][] &mdash; Whether this [Group][msl.io.node.Group] is in read-only mode.

        Setting this value will also update all sub-[Group][msl.io.node.Group]s
        and sub-[Dataset][msl.io.node.Dataset]s to be in the same mode.
        """
        return self._read_only

    @read_only.setter
    def read_only(self, value: bool) -> None:
        val = bool(value)
        self._read_only = val
        self._metadata.read_only = val

        # update all descendants of this Group
        for obj in self._mapping.values():
            obj.read_only = val

    @staticmethod
    def is_dataset(obj: object) -> bool:
        """Check if an object is an instance of [Dataset][msl.io.node.Dataset].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [Dataset][msl.io.node.Dataset].
        """
        return isinstance(obj, Dataset)

    @staticmethod
    def is_dataset_logging(obj: object) -> bool:
        """Check if an object is an instance of [DatasetLogging][msl.io.node.DatasetLogging].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [DatasetLogging][msl.io.node.DatasetLogging].
        """
        return isinstance(obj, DatasetLogging)

    @staticmethod
    def is_group(obj: object) -> bool:
        """Check if an object is an instance of [Group][msl.io.node.Group].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [Group][msl.io.node.Group].
        """
        return isinstance(obj, Group)

    def datasets(self, *, exclude: str | None = None, include: str | None = None, flags: int = 0) -> Iterator[Dataset]:
        """Yield the [Dataset][msl.io.node.Dataset]s in this [Group][msl.io.node.Group].

        Args:
            exclude: A regular-expression pattern to use to exclude [Dataset][msl.io.node.Dataset]s.
                The [re.search][] function is used to compare the `exclude` pattern
                with the [name][msl.io.node.Dataset.name] of each [Dataset][msl.io.node.Dataset]. If
                there is a match, the [Dataset][msl.io.node.Dataset] is not yielded.
            include: A regular-expression pattern to use to include [Dataset][msl.io.node.Dataset]s.
                The [re.search][] function is used to compare the `include` pattern
                with the [name][msl.io.node.Dataset.name] of each [Dataset][msl.io.node.Dataset]. If
                there is a match, the [Dataset][msl.io.node.Dataset] is yielded.
            flags: Regular-expression flags that are passed to [re.compile][].

        Yields:
            The filtered [Dataset][msl.io.node.Dataset]s based on the `exclude` and `include` patterns.
                The `exclude` pattern has more precedence than the `include` pattern if there is a conflict.
        """
        e = None if exclude is None else re.compile(exclude, flags=flags)
        i = None if include is None else re.compile(include, flags=flags)
        for obj in self._mapping.values():
            if isinstance(obj, Dataset):
                if e and e.search(obj.name):
                    continue
                if i and not i.search(obj.name):
                    continue
                yield obj

    def groups(self, *, exclude: str | None = None, include: str | None = None, flags: int = 0) -> Iterator[Group]:
        """Yield the sub-[Group][msl.io.node.Group]s of this [Group][msl.io.node.Group].

        Args:
            exclude: A regular-expression pattern to use to exclude sub-[Group][msl.io.node.Group]s.
                The [re.search][] function is used to compare the `exclude` pattern with the
                [name][msl.io.node.Group.name] of each sub-[Group][msl.io.node.Group]. If there is a match,
                the sub-[Group][msl.io.node.Group] is not yielded.
            include: A regular-expression pattern to use to include sub-[Group][msl.io.node.Group]s.
                The [re.search][] function is used to compare the `include` pattern with the
                [name][msl.io.node.Group.name] of each sub-[Group][msl.io.node.Group]. If there is a match,
                the sub-[Group][msl.io.node.Group] is yielded.
            flags: Regular-expression flags that are passed to [re.compile][].

        Yields:
            The filtered sub-[Group][msl.io.node.Group]s based on the `exclude` and `include` patterns.
                The `exclude` pattern has more precedence than the `include` pattern if there is a conflict.
        """
        e = None if exclude is None else re.compile(exclude, flags=flags)
        i = None if include is None else re.compile(include, flags=flags)
        for obj in self._mapping.values():
            if isinstance(obj, Group):
                if e and e.search(obj.name):
                    continue
                if i and not i.search(obj.name):
                    continue
                yield obj

    def descendants(self) -> Iterator[Group]:
        """Yield all descendant (children) [Group][msl.io.node.Group]s of this [Group][msl.io.node.Group].

        Yields:
            The descendants of this [Group][msl.io.node.Group].
        """
        for obj in self._mapping.values():
            if isinstance(obj, Group):
                yield obj

    def ancestors(self) -> Iterator[Group]:
        """Yield all ancestor (parent) [Group][msl.io.node.Group]s of this [Group][msl.io.node.Group].

        Yields:
            The ancestors of this [Group][msl.io.node.Group].
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def add_group(self, name: str, group: Group) -> None:
        """Add a [Group][msl.io.node.Group].

        Args:
            name: The name of the new [Group][msl.io.node.Group] to add. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist.
            group: The [Group][msl.io.node.Group] to add. The [Dataset][msl.io.node.Dataset]s and
                [Metadata][msl.io.metadata.Metadata] that are contained within the
                `group` will be copied.
        """
        if not isinstance(group, Group):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Must pass in a Group object, got {group!r}"  # type: ignore[unreachable] # pyright: ignore[reportUnreachable]
            raise TypeError(msg)

        name = "/" + name.strip("/")

        if not group:  # no sub-Groups or Datasets, only add the Metadata
            _ = self.create_group(name + group.name, **group.metadata.copy())
            return

        for key, node in group.items():
            n = name + key
            if isinstance(node, Group):
                _ = self.create_group(n, read_only=node.read_only, **node.metadata.copy())
            else:  # must be a Dataset
                _ = self.create_dataset(n, read_only=node.read_only, data=node.data.copy(), **node.metadata.copy())

    def create_group(self, name: str, *, read_only: bool | None = None, **metadata: Any) -> Group:
        """Create a new [Group][msl.io.node.Group].

        Args:
            name: The name of the new [Group][msl.io.node.Group]. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist.
            read_only: Whether to create the new [Group][msl.io.node.Group] in read-only mode.
                If `None`, uses the mode for this [Group][msl.io.node.Group].
            metadata: All additional keyword arguments are used to create the [Metadata][msl.io.metadata.Metadata]
                for the new [Group][msl.io.node.Group].

        Returns:
            The new [Group][msl.io.node.Group] that was created.
        """
        read_only, metadata = self._check(read_only=read_only, **metadata)
        name, parent = self._create_ancestors(name, read_only=read_only)
        return Group(name=name, parent=parent, read_only=read_only, **metadata)

    def require_group(self, name: str, *, read_only: bool | None = None, **metadata: Any) -> Group:
        """Require that a [Group][msl.io.node.Group] exists.

        If the [Group][msl.io.node.Group] exists it will be returned otherwise it is created then returned.

        Args:
            name: The name of the [Group][msl.io.node.Group] to require. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist.
            read_only: Whether to return the required [Group][msl.io.node.Group] in read-only mode.
                If `None`, uses the mode for this [Group][msl.io.node.Group].
            metadata: All additional keyword arguments are used as [Metadata][msl.io.metadata.Metadata]
                for the required [Group][msl.io.node.Group].

        Returns:
            The required [Group][msl.io.node.Group] that was created or that already existed.
        """
        name = "/" + name.strip("/")
        group_name = name if self.parent is None else self.name + name
        for group in self.groups():
            if group.name == group_name:
                if read_only is not None:
                    group.read_only = read_only
                group.add_metadata(**metadata)
                return group
        return self.create_group(name, read_only=read_only, **metadata)

    def add_dataset(self, name: str, dataset: Dataset) -> None:
        """Add a [Dataset][msl.io.node.Dataset].

        Args:
            name: The name of the new [Dataset][msl.io.node.Dataset] to add. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist.
            dataset: The [Dataset][msl.io.node.Dataset] to add. The data and the
                [Metadata][msl.io.metadata.Metadata] in the [Dataset][msl.io.node.Dataset] are copied.
        """
        if not isinstance(dataset, Dataset):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Must pass in a Dataset object, got {dataset!r}"  # type: ignore[unreachable] # pyright: ignore[reportUnreachable]
            raise TypeError(msg)

        name = "/" + name.strip("/")
        _ = self.create_dataset(name, read_only=dataset.read_only, data=dataset.data.copy(), **dataset.metadata.copy())

    def create_dataset(self, name: str, *, read_only: bool | None = None, **kwargs: Any) -> Dataset:
        """Create a new [Dataset][msl.io.node.Dataset].

        Args:
            name: The name of the new [Dataset][msl.io.node.Dataset]. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist. See [here][automatic-group-creation]
                for an example.
            read_only: Whether to create the new [Dataset][msl.io.node.Dataset] in read-only mode.
                If `None`, uses the mode for this [Group][msl.io.node.Group].
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.node.Dataset].

        Returns:
            The new [Dataset][msl.io.node.Dataset] that was created.
        """
        read_only, kwargs = self._check(read_only=read_only, **kwargs)
        name, parent = self._create_ancestors(name, read_only=read_only)
        return Dataset(name=name, parent=parent, read_only=read_only, **kwargs)

    def require_dataset(self, name: str, *, read_only: bool | None = None, **kwargs: Any) -> Dataset:
        """Require that a [Dataset][msl.io.node.Dataset] exists.

        If the [Dataset][msl.io.node.Dataset] exists it will be returned, otherwise it is created then returned.

        Args:
            name: The name of the required [Dataset][msl.io.node.Dataset]. Automatically creates the ancestor
                [Group][msl.io.node.Group]s if they do not exist.
            read_only: Whether to create the required [Dataset][msl.io.node.Dataset] in read-only mode.
                If `None`, uses the mode for this [Group][msl.io.node.Group].
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.node.Dataset].

        Returns:
            The [Dataset][msl.io.node.Dataset] that was created or that already existed.
        """
        name = "/" + name.strip("/")
        dataset_name = name if self.parent is None else self.name + name
        for dataset in self.datasets():
            if dataset.name == dataset_name:
                if read_only is not None:
                    dataset.read_only = read_only
                if kwargs:  # only add the kwargs that should be Metadata
                    for kw in ["shape", "dtype", "buffer", "offset", "strides", "order", "data"]:
                        kwargs.pop(kw, None)
                dataset.add_metadata(**kwargs)
                return dataset
        return self.create_dataset(name, read_only=read_only, **kwargs)

    def add_dataset_logging(self, name: str, dataset_logging: DatasetLogging) -> None:
        """Add a [DatasetLogging][msl.io.node.DatasetLogging].

        Args:
            name: The name of the new [DatasetLogging][msl.io.node.DatasetLogging] to add.
                Automatically creates the ancestor [Group][msl.io.node.Group]s if they do not exist.
            dataset_logging: The [DatasetLogging][msl.io.node.DatasetLogging] to add. The
                data and [Metadata][msl.io.metadata.Metadata] are copied.
        """
        if not isinstance(dataset_logging, DatasetLogging):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Must pass in a DatasetLogging object, got {dataset_logging!r}"  # type: ignore[unreachable] # pyright: ignore[reportUnreachable]
            raise TypeError(msg)

        name = "/" + name.strip("/")
        _ = self.create_dataset_logging(
            name,
            level=dataset_logging.level,
            attributes=dataset_logging.attributes,
            logger=dataset_logging.logger,
            date_fmt=dataset_logging.date_fmt,
            data=dataset_logging.data.copy(),
            **dataset_logging.metadata.copy(),
        )

    def create_dataset_logging(
        self,
        name: str,
        *,
        level: str | int = "INFO",
        attributes: Sequence[str] | None = None,
        logger: Logger | None = None,
        date_fmt: str | None = None,
        **kwargs: Any,
    ) -> DatasetLogging:
        """Create a [Dataset][msl.io.node.Dataset] that handles [logging][] records.

        !!! example "See [here][msl-io-dataset-logging] for an example."

        Args:
            name: A name to associate with the [Dataset][msl.io.node.Dataset].
                Automatically creates the ancestor [Group][msl.io.node.Group]s if they do not exist.
            level: The [logging level][levels] to use.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.node.Dataset] for each [logging record][log-record].
                If `None`, uses _asctime_, _levelname_, _name_, and _message_.
            logger: The [Logger][logging.Logger] that the [DatasetLogging][msl.io.node.DatasetLogging] object
                will be associated with. If `None`, it is associated with the _root_ [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] in.
                If `None`, uses the ISO 8601 format `"%Y-%m-%dT%H:%M:%S.%f"`.
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.node.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.node.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.node.Dataset] is equal to the number of
                [logging records][log-record] that were added to it. However, this behaviour
                can decrease performance if many [logging records][log-record] are
                added often because a copy of the data in the [Dataset][msl.io.node.Dataset] is
                created for each [logging record][log-record] that is added. You can improve
                performance by specifying an initial size of the [Dataset][msl.io.node.Dataset]
                by including a `shape` or a `size` keyword argument. This will also automatically
                create additional empty rows in the [Dataset][msl.io.node.Dataset], that is
                proportional to the size of the [Dataset][msl.io.node.Dataset], if the size of the
                [Dataset][msl.io.node.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.node.DatasetLogging.remove_empty_rows] before
                writing [DatasetLogging][msl.io.node.DatasetLogging] to a file or interacting
                with the data in [DatasetLogging][msl.io.node.DatasetLogging] to remove the
                _empty_ rows that were created.

        Returns:
            The [DatasetLogging][msl.io.node.DatasetLogging] that was created.
        """
        read_only, metadata = self._check(read_only=False, **kwargs)
        name, parent = self._create_ancestors(name, read_only=read_only)
        if attributes is None:
            # if the default attribute names are changed then update the `attributes`
            # description in the docstring of create_dataset_logging() and require_dataset_logging()
            attributes = ["asctime", "levelname", "name", "message"]
        if date_fmt is None:
            # if the default date_fmt is changed then update the `date_fmt`
            # description in the docstring of create_dataset_logging() and require_dataset_logging()
            date_fmt = "%Y-%m-%dT%H:%M:%S.%f"
        return DatasetLogging(
            name=name, parent=parent, level=level, attributes=attributes, logger=logger, date_fmt=date_fmt, **metadata
        )

    def require_dataset_logging(
        self,
        name: str,
        *,
        level: str | int = "INFO",
        attributes: Sequence[str] | None = None,
        logger: Logger | None = None,
        date_fmt: str | None = None,
        **kwargs: Any,
    ) -> DatasetLogging:
        """Require that a [Dataset][msl.io.node.Dataset] exists for handling [logging][] records.

        If the [DatasetLogging][msl.io.node.DatasetLogging] exists it will be returned
        otherwise it is created and then returned.

        Args:
            name: A name to associate with the [Dataset][msl.io.node.Dataset].
                Automatically creates the ancestor [Group][msl.io.node.Group]s if they do not exist.
            level: The [logging level][levels] to use.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.node.Dataset] for each [logging record][log-record].
                If `None`, uses _asctime_, _levelname_, _name_, and _message_.
            logger: The [Logger][logging.Logger] that the [DatasetLogging][msl.io.node.DatasetLogging] object
                will be associated with. If `None`, it is associated with the _root_ [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] in.
                If `None`, uses the ISO 8601 format `"%Y-%m-%dT%H:%M:%S.%f"`.
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.node.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.node.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.node.Dataset] is equal to the number of
                [logging records][log-record] that were added to it. However, this behaviour
                can decrease performance if many [logging records][log-record] are
                added often because a copy of the data in the [Dataset][msl.io.node.Dataset] is
                created for each [logging record][log-record] that is added. You can improve
                performance by specifying an initial size of the [Dataset][msl.io.node.Dataset]
                by including a `shape` or a `size` keyword argument. This will also automatically
                create additional empty rows in the [Dataset][msl.io.node.Dataset], that is
                proportional to the size of the [Dataset][msl.io.node.Dataset], if the size of the
                [Dataset][msl.io.node.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.node.DatasetLogging.remove_empty_rows] before
                writing [DatasetLogging][msl.io.node.DatasetLogging] to a file or interacting
                with the data in [DatasetLogging][msl.io.node.DatasetLogging] to remove the
                _empty_ rows that were created.

        Returns:
            The [DatasetLogging][msl.io.node.DatasetLogging] that was created or that already existed.
        """
        name = "/" + name.strip("/")
        dataset_name = name if self.parent is None else self.name + name
        for dataset in self.datasets():
            if dataset.name == dataset_name:
                if (
                    ("logging_level" not in dataset.metadata)
                    or ("logging_level_name" not in dataset.metadata)
                    or ("logging_date_format" not in dataset.metadata)
                ):
                    msg = "The required Dataset was found but it is not used for logging"
                    raise ValueError(msg)

                if attributes and (dataset.dtype.names != tuple(attributes)):
                    msg = (
                        f"The attribute names of the existing logging Dataset are "
                        f"{dataset.dtype.names} which does not equal {tuple(attributes)}"
                    )
                    raise ValueError(msg)

                if isinstance(dataset, DatasetLogging):
                    return dataset

                # replace the existing Dataset with a new DatasetLogging object
                meta = dataset.metadata.copy()
                data = dataset.data.copy()

                # remove the existing Dataset from its descendants, itself and its ancestors
                groups = (*tuple(self.descendants()), self, *tuple(self.ancestors()))
                for group in groups:
                    for dset in group.datasets():
                        if dset is dataset:
                            key = "/" + dset.name.lstrip(group.name)
                            del group._mapping[key]  # noqa: SLF001
                            break

                # temporarily make this Group not in read-only mode
                original_read_only_mode = bool(self._read_only)
                self._read_only: bool = False
                kwargs.update(meta)
                dset = self.create_dataset_logging(
                    name,
                    level=level,
                    attributes=data.dtype.names,
                    logger=logger,
                    date_fmt=meta.logging_date_format,
                    data=data,
                    **kwargs,
                )
                self._read_only = original_read_only_mode
                return dset

        return self.create_dataset_logging(
            name, level=level, attributes=attributes, logger=logger, date_fmt=date_fmt, **kwargs
        )

    def remove(self, name: str) -> Dataset | Group | None:
        """Remove a [Group][msl.io.node.Group] or a [Dataset][msl.io.node.Dataset].

        Args:
            name: The name of the [Group][msl.io.node.Group] or [Dataset][msl.io.node.Dataset] to remove.

        Returns:
            The [Group][msl.io.node.Group] or [Dataset][msl.io.node.Dataset] that was removed or `None` if
                there was no [Group][msl.io.node.Group] or [Dataset][msl.io.node.Dataset] with the specified `name`.
        """
        name = "/" + name.strip("/")
        return self.pop(name, None)

    def _check(self, *, read_only: bool | None, **kwargs: Any) -> tuple[bool, dict[str, Any]]:
        self._raise_if_read_only()
        kwargs.pop("parent", None)
        if read_only is None:
            return self._read_only, kwargs
        return read_only, kwargs

    def _create_ancestors(self, name: str, *, read_only: bool) -> tuple[str, Group]:
        """Automatically creates the ancestor Groups if they do not already exist."""
        names = name.strip("/").split("/")
        group: Group = self
        for n in names[:-1]:
            try:
                group = group[n]  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
                assert isinstance(group, Group)  # noqa: S101
            except KeyError:  # noqa: PERF203
                group = Group(name=n, parent=group, read_only=read_only)
        return names[-1], group


def _unix_name(name: str, parent: Group | None) -> str:
    """Returns the name of a node using a path name similar to a UNIX file system."""
    if not name:
        msg = "The name cannot be an empty string"
        raise ValueError(msg)

    if parent is None:
        return name

    if "/" in name:
        msg = "The name cannot contain the '/' character"
        raise ValueError(msg)

    pn = parent.name
    return f"{pn}{name}" if pn.endswith("/") else f"{pn}/{name}"


def _notify_created(node: Dataset | Group, parent: Group | None) -> None:
    """Notify all ancestors that this node was created."""
    i = 0
    name_split = node.name.split("/")
    while parent is not None:
        i += 1
        key = "/" + "/".join(name_split[-i:])
        if key in parent:
            msg = f"The name, {key!r}, is not unique"
            raise ValueError(msg)
        # A node may be set to read_only=False, but its ancestor may be read_only=True.
        # Therefore _mapping must be accessed directly (instead of parent[key]) to notify
        # the ancestor that this node now exists
        parent._mapping[key] = node  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        parent = parent.parent
