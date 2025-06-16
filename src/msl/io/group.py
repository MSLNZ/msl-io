"""A [Group][] can contain sub-[Group][]s and/or [Dataset][msl.io.dataset.Dataset]s."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .vertex import Dataset, DatasetLogging, Vertex

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from logging import Logger
    from typing import Any


class Group(Vertex):
    """A [Group][] can contain sub-[Group][]s and/or [Dataset][msl.io.vertex.Dataset]s."""

    def __init__(self, *, name: str, parent: Group | None, read_only: bool, **metadata: Any) -> None:
        """A [Group][] can contain sub-[Group][]s and/or [Dataset][msl.io.vertex.Dataset]s.

        !!! attention
            Do not instantiate directly. Create a new [Group][] using [create_group][msl.io.group.Group.create_group].

        Args:
            name: The name of this [Group][]. Uses a naming convention analogous to UNIX
                file systems where each [Group][msl.io.group.Group] can be thought
                of as a directory and where every subdirectory is separated from its
                parent directory by the `"/"` character.
            parent: The parent to this [Group][].
            read_only: Whether the [Group][] is initialised in read-only mode.
            metadata: All additional keyword arguments are used to create the
                [Metadata][msl.io.metadata.Metadata] for this [Group][].
        """
        super().__init__(name=name, parent=parent, read_only=read_only, **metadata)

    def __repr__(self) -> str:
        """Returns the string representation of the `Group`."""
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        return f"<Group {self._name!r} ({g} groups, {d} datasets, {m} metadata)>"

    def __getitem__(self, item: str) -> Dataset | Group:
        """Get an item from the `Group`."""
        if item and item[0] != "/":
            item = "/" + item

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
            return self.__delitem__("/" + item)
        except KeyError as e:
            raise AttributeError(str(e)) from None

    @staticmethod
    def is_dataset(obj: object) -> bool:
        """Check if an object is an instance of [Dataset][msl.io.vertex.Dataset].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [Dataset][msl.io.vertex.Dataset].
        """
        return isinstance(obj, Dataset)

    @staticmethod
    def is_dataset_logging(obj: object) -> bool:
        """Check if an object is an instance of [DatasetLogging][msl.io.vertex.DatasetLogging].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [DatasetLogging][msl.io.vertex.DatasetLogging].
        """
        return isinstance(obj, DatasetLogging)

    @staticmethod
    def is_group(obj: object) -> bool:
        """Check if an object is an instance of [Group][msl.io.group.Group].

        Args:
            obj: The object to check.

        Returns:
            Whether `obj` is an instance of [Group][msl.io.group.Group].
        """
        return isinstance(obj, Group)

    def datasets(self, *, exclude: str | None = None, include: str | None = None, flags: int = 0) -> Iterator[Dataset]:
        """Yield the [Dataset][msl.io.vertex.Dataset]s in this [Group][].

        Args:
            exclude: A regular-expression pattern to use to exclude [Dataset][msl.io.vertex.Dataset]s.
                The [re.search][] function is used to compare the `exclude` pattern
                with the `name` of each [Dataset][msl.io.vertex.Dataset]. If
                there is a match, the [Dataset][msl.io.vertex.Dataset] is not yielded.
            include: A regular-expression pattern to use to include [Dataset][msl.io.vertex.Dataset]s.
                The [re.search][] function is used to compare the `include` pattern
                with the `name` of each [Dataset][msl.io.vertex.Dataset]. If
                there is a match, the [Dataset][msl.io.vertex.Dataset] is yielded.
            flags: Regular-expression flags that are passed to [re.compile][].

        Yields:
            The filtered [Dataset][msl.io.vertex.Dataset]s based on the `exclude` and `include` patterns.
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
        """Yield the sub-[Group][]s of this [Group][].

        Args:
            exclude: A regular-expression pattern to use to exclude sub-[Group][msl.io.group.Group]s.
                The [re.search][] function is used to compare the `exclude` pattern with the `name`
                of each sub-[Group][]. If there is a match, the sub-[Group][] is not yielded.
            include: A regular-expression pattern to use to include sub-[Group][]s. The
                [re.search][] function is used to compare the `include` pattern with the
                `name` of each sub-[Group][]. If there is a match, the sub-[Group][] is yielded.
            flags: Regular-expression flags that are passed to [re.compile][].

        Yields:
            The filtered sub-[Group][]s based on the `exclude` and `include` patterns.
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
        """Yield all descendant (children) [Group][]s of this [Group][].

        Yields:
            The descendants of this [Group][].
        """
        for obj in self._mapping.values():
            if isinstance(obj, Group):
                yield obj

    def ancestors(self) -> Iterator[Group]:
        """Yield all ancestor (parent) [Group][]s of this [Group][].

        Yields:
            The ancestors of this [Group][].
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def add_group(self, name: str, group: Group) -> None:
        """Add a [Group][].

        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the new [Group][] to add.
            group: The [Group][] to add. The [Dataset][msl.io.vertex.Dataset]s and
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

        for key, vertex in group.items():
            n = name + key
            if isinstance(vertex, Group):
                _ = self.create_group(n, read_only=vertex.read_only, **vertex.metadata.copy())
            else:  # must be a Dataset
                _ = self.create_dataset(
                    n, read_only=vertex.read_only, data=vertex.data.copy(), **vertex.metadata.copy()
                )

    def create_group(self, name: str, *, read_only: bool | None = None, **metadata: Any) -> Group:
        """Create a new [Group][].

        Automatically creates the ancestor[Group][]s if they do not exist.

        Args:
            name: The name of the new [Group][].
            read_only: Whether to create the new [Group][] in read-only mode.
                If `None`, uses the mode for this [Group][].
            metadata: All additional keyword arguments are used to create the [Metadata][msl.io.metadata.Metadata]
                for the new [Group][].

        Returns:
            The new [Group][] that was created.
        """
        read_only, metadata = self._check(read_only=read_only, **metadata)
        name, parent = self._create_ancestors(name, read_only=read_only)
        return Group(name=name, parent=parent, read_only=read_only, **metadata)

    def require_group(self, name: str, read_only: bool | None = None, **metadata: Any) -> Group:
        """Require that a [Group][] exists.

        If the [Group][] exists, it will be returned otherwise it is created then returned.
        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the [Group][] to require.
            read_only: Whether to return the required [Group][] in read-only mode.
                If `None`, uses the mode for this [Group][].
            metadata: All additional keyword arguments are used as [Metadata][msl.io.metadata.Metadata]
                for the required [Group][].

        Returns:
            The required [Group][] that was created or that already existed.
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
        """Add a [Dataset][msl.io.vertex.Dataset].

        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the new [Dataset][msl.io.vertex.Dataset] to add.
            dataset: The [Dataset][msl.io.vertex.Dataset] to add. The data and the
                [Metadata][msl.io.metadata.Metadata] in the [Dataset][msl.io.vertex.Dataset] are copied.
        """
        if not isinstance(dataset, Dataset):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Must pass in a Dataset object, got {dataset!r}"  # type: ignore[unreachable] # pyright: ignore[reportUnreachable]
            raise TypeError(msg)

        name = "/" + name.strip("/")
        _ = self.create_dataset(name, read_only=dataset.read_only, data=dataset.data.copy(), **dataset.metadata.copy())

    def create_dataset(self, name: str, *, read_only: bool | None = None, **kwargs: Any) -> Dataset:
        """Create a new [Dataset][msl.io.vertex.Dataset].

        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the new [Dataset][msl.io.vertex.Dataset].
            read_only: Whether to create this [Dataset][msl.io.vertex.Dataset] in read-only mode.
                If `None`, uses the mode for this [Group][].
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.vertex.Dataset].

        Returns:
            The new [Dataset][msl.io.vertex.Dataset] that was created.
        """
        read_only, kwargs = self._check(read_only=read_only, **kwargs)
        name, parent = self._create_ancestors(name, read_only=read_only)
        return Dataset(name=name, parent=parent, read_only=read_only, **kwargs)

    def require_dataset(self, name: str, *, read_only: bool | None = None, **kwargs: Any) -> Dataset:
        """Require that a [Dataset][msl.io.vertex.Dataset] exists.

        If the [Dataset][msl.io.vertex.Dataset] exists it will be returned, otherwise it is created then returned.
        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the required [Dataset][msl.io.vertex.Dataset].
            read_only: Whether to create the required [Dataset][msl.io.vertex.Dataset] in read-only mode.
                If `None`, uses the mode for this [Group][].
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.vertex.Dataset].

        Returns:
            The [Dataset][msl.io.vertex.Dataset] that was created or that already existed.
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
        """Add a [DatasetLogging][msl.io.vertex.DatasetLogging].

        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: The name of the new [DatasetLogging][msl.io.vertex.DatasetLogging] to add.
            dataset_logging: The [DatasetLogging][msl.io.vertex.DatasetLogging] to add. The
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
        """Create a [Dataset][msl.io.vertex.Dataset] that handles [logging][] records.

        Automatically creates the ancestor [Group][]s if they do not exist.

        Args:
            name: A name to associate with the [Dataset][msl.io.vertex.Dataset].
            level: The [logging level][levels] to use.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.vertex.Dataset] for each [logging record][log-record].
                If `None`, uses _asctime_, _levelname_, _name_, and _message_.
            logger: The [Logger][logging.Logger] that the [DatasetLogging][msl.io.vertex.DatasetLogging] object
                will be added to. If `None`, it is added to the `root` [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] in.
                If `None`, uses the ISO 8601 format `"%Y-%m-%dT%H:%M:%S.%f"`.
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.vertex.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.vertex.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.vertex.Dataset] is equal to the number of
                [logging records][log-record] that were added to it. However, this behaviour
                can decrease the performance if many [logging records][log-record] are
                added often because a copy of the data in the [Dataset][msl.io.vertex.Dataset] is
                created for each [logging record][log-record] that is added. You can improve
                the performance by specifying an initial size of the [Dataset][msl.io.vertex.Dataset]
                by including a `shape` or a `size` keyword argument. This will also automatically
                create additional empty rows in the [Dataset][msl.io.vertex.Dataset], that is
                proportional to the size of the [Dataset][msl.io.vertex.Dataset], if the size of the
                [Dataset][msl.io.vertex.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.vertex.DatasetLogging.remove_empty_rows] before
                writing [DatasetLogging][msl.io.vertex.DatasetLogging] to a file or interacting
                with the data in [DatasetLogging][msl.io.vertex.DatasetLogging] to remove the
                _empty_ rows that were created.

        Returns:
            The [DatasetLogging][msl.io.vertex.DatasetLogging] that was created.

        Examples:
        >>> import logging
        >>> from msl.io import JSONWriter
        >>> logger = logging.getLogger('my_logger')
        >>> root = JSONWriter()
        >>> log_dset = root.create_dataset_logging('log')
        >>> logger.info('hi')
        >>> logger.error('cannot do that!')
        >>> log_dset.data
        array([(..., 'INFO', 'my_logger', 'hi'), (..., 'ERROR', 'my_logger', 'cannot do that!')],
              dtype=[('asctime', 'O'), ('levelname', 'O'), ('name', 'O'), ('message', 'O')])

        Get all ``ERROR`` :ref:`logging records <log-record>`

        >>> errors = log_dset[log_dset['levelname'] == 'ERROR']
        >>> print(errors)
        [(..., 'ERROR', 'my_logger', 'cannot do that!')]

        Stop the :class:`~msl.io.dataset_logging.DatasetLogging` object
        from receiving :ref:`logging records <log-record>`

        >>> log_dset.remove_handler()
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
        """Require that a [Dataset][msl.io.vertex.Dataset] exists for handling [logging][] records.

        If the [DatasetLogging][msl.io.dataset_logging.DatasetLogging] exists it will be returned
        otherwise it is created and then returned. Automatically creates the ancestor [Group][]s
        if they do not exist.

            name: A name to associate with the [Dataset][msl.io.vertex.Dataset].
            level: The [logging level][levels] to use.
            attributes: The [attribute names][logrecord-attributes] to include in the
                [Dataset][msl.io.vertex.Dataset] for each [logging record][log-record].
                If `None`, uses _asctime_, _levelname_, _name_, and _message_.
            logger: The [Logger][logging.Logger] that the [DatasetLogging][msl.io.vertex.DatasetLogging] object
                will be added to. If `None`, it is added to the `root` [Logger][logging.Logger].
            date_fmt: The [datetime][datetime.datetime] [format code][strftime-strptime-behavior]
                to use to represent the _asctime_ [attribute][logrecord-attributes] in.
                If `None`, uses the ISO 8601 format `"%Y-%m-%dT%H:%M:%S.%f"`.
            kwargs: All additional keyword arguments are passed to [Dataset][msl.io.vertex.Dataset].
                The default behaviour is to append every [logging record][log-record]
                to the [Dataset][msl.io.vertex.Dataset]. This guarantees that the size of the
                [Dataset][msl.io.vertex.Dataset] is equal to the number of
                [logging records][log-record] that were added to it. However, this behaviour
                can decrease the performance if many [logging records][log-record] are
                added often because a copy of the data in the [Dataset][msl.io.vertex.Dataset] is
                created for each [logging record][log-record] that is added. You can improve
                the performance by specifying an initial size of the [Dataset][msl.io.vertex.Dataset]
                by including a `shape` or a `size` keyword argument. This will also automatically
                create additional empty rows in the [Dataset][msl.io.vertex.Dataset], that is
                proportional to the size of the [Dataset][msl.io.vertex.Dataset], if the size of the
                [Dataset][msl.io.vertex.Dataset] needs to be increased. If you do this then you will
                want to call [remove_empty_rows][msl.io.vertex.DatasetLogging.remove_empty_rows] before
                writing [DatasetLogging][msl.io.vertex.DatasetLogging] to a file or interacting
                with the data in [DatasetLogging][msl.io.vertex.DatasetLogging] to remove the
                _empty_ rows that were created.

        Returns:
            The [DatasetLogging][msl.io.vertex.DatasetLogging] that was created or that already existed.
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
        """Remove a [Group][] or a [Dataset][msl.io.vertex.Dataset].

        Args:
            name: The name of the [Group][] or [Dataset][msl.io.vertex.Dataset] to remove.

        Returns:
            The [Group][] or [Dataset][msl.io.vertex.Dataset] that was removed or `None` if
            there was no [Group][] or [Dataset][msl.io.vertex.Dataset] with the specified `name`.
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
        # automatically create the ancestor Groups if they do not already exist
        names = name.strip("/").split("/")
        parent: Group = self
        for n in names[:-1]:
            parent = Group(name=n, parent=parent, read_only=read_only) if n not in parent else parent[n]
            assert isinstance(parent, Group)  # noqa: S101
        return names[-1], parent
