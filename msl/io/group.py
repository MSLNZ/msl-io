"""
A :class:`Group` can contain sub-:class:`Group`\\s and/or :class:`~msl.io.dataset.Dataset`\\s.
"""
from .vertex import Vertex
from .dataset import Dataset
from .dataset_logging import DatasetLogging


class Group(Vertex):

    def __init__(self, name, parent, is_read_only, **metadata):
        """A :class:`Group` can contain sub-:class:`Group`\\s and/or :class:`~msl.io.dataset.Dataset`\\s.

        Do not instantiate directly. Create a new :class:`Group` using
        :meth:`~msl.io.group.Group.create_group`.

        Parameters
        ----------
        name : :class:`str`
            The name of this :class:`Group`. Uses a naming convention analogous to UNIX
            file systems where each :class:`~msl.io.group.Group` can be thought
            of as a directory and where every subdirectory is separated from its
            parent directory by the ``'/'`` character.
        parent : :class:`Group`
            The parent :class:`Group` to this :class:`Group`.
        is_read_only : :class:`bool`
            Whether the :class:`Group` is to be accessed in read-only mode.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for this :class:`Group`.
        """
        super(Group, self).__init__(name, parent, is_read_only, **metadata)

    def __repr__(self):
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        return '<Group {!r} ({} groups, {} datasets, {} metadata)>'.format(self._name, g, d, m)

    def __getitem__(self, item):
        if item and not item[0] == '/':
            item = '/' + item
        try:
            return self._mapping[item]
        except KeyError:
            pass  # raise a more detailed error message below
        self._raise_key_error(item)

    def __getattr__(self, item):
        try:
            return self.__getitem__('/' + item)
        except KeyError as e:
            msg = str(e)
        raise AttributeError(msg)

    def __delattr__(self, item):
        try:
            return self.__delitem__('/' + item)
        except KeyError as e:
            msg = str(e)
        raise AttributeError(msg)

    @staticmethod
    def is_dataset(obj):
        """Test whether an object is a :class:`~msl.io.dataset.Dataset`.

        Parameters
        ----------
        obj : :class:`object`
            The object to test.

        Returns
        -------
        :class:`bool`
            Whether `obj` is an instance of :class:`~msl.io.dataset.Dataset`.
        """
        return isinstance(obj, Dataset)

    @staticmethod
    def is_dataset_logging(obj):
        """Test whether an object is a :class:`~msl.io.dataset_logging.DatasetLogging`.

        Parameters
        ----------
        obj : :class:`object`
            The object to test.

        Returns
        -------
        :class:`bool`
            Whether `obj` is an instance of :class:`~msl.io.dataset_logging.DatasetLogging`.
        """
        return isinstance(obj, DatasetLogging)

    @staticmethod
    def is_group(obj):
        """Test whether an object is a :class:`~msl.io.group.Group`.

        Parameters
        ----------
        obj : :class:`object`
            The object to test.

        Returns
        -------
        :class:`bool`
            Whether `obj` is an instance of :class:`~msl.io.group.Group`.
        """
        return isinstance(obj, Group)

    def datasets(self):
        """Get all :class:`~msl.io.dataset.Dataset`\\s of this :class:`Group`.

        Yields
        ------
        :class:`~msl.io.dataset.Dataset`
            All :class:`~msl.io.dataset.Dataset`\\s that are contained within
            this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_dataset(obj):
                yield obj

    def groups(self):
        """Get all sub-:class:`Group`\\s (descendants) of this :class:`Group`.

        Yields
        ------
        :class:`Group`
            All sub-:class:`Group`\\s (descendants) that are contained within
            this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_group(obj):
                yield obj

    descendants = groups

    def ancestors(self):
        """Get all parent :class:`Group`\\s (ancestors) of this :class:`Group`.

        Yields
        ------
        :class:`Group`
            The ancestors of this :class:`Group`.
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def add_group(self, name, group):
        """Add a :class:`Group`.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`Group` to add.
        group : :class:`Group`
            The :class:`Group` to add. The :class:`~msl.io.dataset.Dataset`\\s and
            :class:`~msl.io.metadata.Metadata` that are contained within the
            `group` will be copied.
        """
        if not isinstance(group, Group):
            raise TypeError('Must pass in a Group object, got {!r}'.format(group))

        name = '/' + name.strip('/')

        if not group:  # no sub-Groups or Datasets, only add the Metadata
            self.create_group(name + group.name, **group.metadata.copy())
            return

        for key, vertex in group.items():
            n = name + key
            if self.is_group(vertex):
                self.create_group(n, is_read_only=vertex.is_read_only, **vertex.metadata.copy())
            else:  # must be a Dataset
                self.create_dataset(
                    n, is_read_only=vertex.is_read_only, data=vertex.data.copy(), **vertex.metadata.copy()
                )

    def create_group(self, name, is_read_only=None, **metadata):
        """Create a new :class:`Group`.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`Group`.
        is_read_only : :class:`bool`, optional
            Whether to create this :class:`Group` in read-only mode.
            If :data:`None` then uses the mode for this :class:`Group`.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for this :class:`Group`.

        Returns
        -------
        :class:`Group`
            The new :class:`Group` that was created.
        """
        is_read_only, metadata = self._check(is_read_only, **metadata)
        name, parent = self._create_ancestors(name, is_read_only)
        return Group(name, parent, is_read_only, **metadata)

    def require_group(self, name, is_read_only=None, **metadata):
        """Require that a :class:`Group` exists.

        If the :class:`Group` exists then it will be returned if it does not exist
        then it is created.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the :class:`Group`.
        is_read_only : :class:`bool`, optional
            Whether to return the :class:`Group` in read-only mode.
            If :data:`None` then uses the mode for this :class:`Group`.
        **metadata
            Key-value pairs that are used as :class:`~msl.io.metadata.Metadata`
            for this :class:`Group`.

        Returns
        -------
        :class:`Group`
            The :class:`Group` that was created or that already existed.
        """
        name = '/' + name.strip('/')
        group_name = name if self.parent is None else self.name + name
        for group in self.groups():
            if group.name == group_name:
                if is_read_only is not None:
                    group.is_read_only = is_read_only
                group.add_metadata(**metadata)
                return group
        return self.create_group(name, is_read_only=is_read_only, **metadata)

    def add_dataset(self, name, dataset):
        """Add a :class:`~msl.io.dataset.Dataset`.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`~msl.io.dataset.Dataset` to add.
        dataset : :class:`~msl.io.dataset.Dataset`
            The :class:`~msl.io.dataset.Dataset` to add. The :class:`~msl.io.dataset.Dataset`
            and the :class:`~msl.io.metadata.Metadata` are copied.
        """
        if not isinstance(dataset, Dataset):
            raise TypeError('Must pass in a Dataset object, got {!r}'.format(dataset))

        name = '/' + name.strip('/')
        self.create_dataset(
            name, is_read_only=dataset.is_read_only, data=dataset.data.copy(), **dataset.metadata.copy()
        )

    def create_dataset(self, name, is_read_only=None, **kwargs):
        """Create a new :class:`~msl.io.dataset.Dataset`.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`~msl.io.dataset.Dataset`.
        is_read_only : :class:`bool`, optional
            Whether to create this :class:`~msl.io.dataset.Dataset` in read-only mode.
            If :data:`None` then uses the mode for this :class:`Group`.
        **kwargs
            Key-value pairs that are passed to :class:`~msl.io.dataset.Dataset`.

        Returns
        -------
        :class:`~msl.io.dataset.Dataset`
            The new :class:`~msl.io.dataset.Dataset` that was created.
        """
        is_read_only, kwargs = self._check(is_read_only, **kwargs)
        name, parent = self._create_ancestors(name, is_read_only)
        return Dataset(name, parent, is_read_only, **kwargs)

    def require_dataset(self, name, is_read_only=None, **kwargs):
        """Require that a :class:`~msl.io.dataset.Dataset` exists.

        If the :class:`~msl.io.dataset.Dataset` exists then it will be returned
        if it does not exist then it is created.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the :class:`~msl.io.dataset.Dataset`.
        is_read_only : :class:`bool`, optional
            Whether to create this :class:`~msl.io.dataset.Dataset` in read-only mode.
            If :data:`None` then uses the mode for this :class:`Group`.
        **kwargs
            Key-value pairs that are passed to :class:`~msl.io.dataset.Dataset`.

        Returns
        -------
        :class:`~msl.io.dataset.Dataset`
            The :class:`~msl.io.dataset.Dataset` that was created or that already existed.
        """
        name = '/' + name.strip('/')
        dataset_name = name if self.parent is None else self.name + name
        for dataset in self.datasets():
            if dataset.name == dataset_name:
                if is_read_only is not None:
                    dataset.is_read_only = is_read_only
                if kwargs:  # only add the kwargs that should be Metadata
                    for kw in ['shape', 'dtype', 'buffer', 'offset', 'strides', 'order', 'data']:
                        kwargs.pop(kw, None)
                dataset.add_metadata(**kwargs)
                return dataset
        return self.create_dataset(name, is_read_only=is_read_only, **kwargs)

    def add_dataset_logging(self, name, dataset_logging):
        """Add a :class:`~msl.io.dataset_logging.DatasetLogging`.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`~msl.io.dataset_logging.DatasetLogging` to add.
        dataset_logging : :class:`~msl.io.dataset_logging.DatasetLogging`
            The :class:`~msl.io.dataset_logging.DatasetLogging` to add. The
            :class:`~msl.io.dataset_logging.DatasetLogging` and the
            :class:`~msl.io.metadata.Metadata` are copied.
        """
        if not isinstance(dataset_logging, DatasetLogging):
            raise TypeError('Must pass in a DatasetLogging object, got {!r}'.format(dataset_logging))

        name = '/' + name.strip('/')
        self.create_dataset_logging(
            name,
            level=dataset_logging.level,
            attributes=dataset_logging.attributes,
            logger=dataset_logging.logger,
            date_fmt=dataset_logging.date_fmt,
            data=dataset_logging.data.copy(),
            **dataset_logging.metadata.copy()
        )

    def create_dataset_logging(self, name, level='INFO', attributes=None, logger=None, date_fmt=None, **kwargs):
        """Create a :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`, optional
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` or :class:`tuple` of :class:`str`, optional
            The :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
            If :data:`None` then uses ``asctime``, ``levelname``, ``name``, and ``message``.
        logger : :class:`~logging.Logger`, optional
            The :class:`~logging.Logger` that the :class:`~msl.io.dataset_logging.DatasetLogging` object
            will be added to. If :data:`None` then it is added to the ``root`` :class:`~logging.Logger`.
        date_fmt : :class:`str`, optional
            The :class:`~datetime.datetime` :ref:`format code <strftime-strptime-behavior>`
            to use to represent the ``asctime`` :ref:`attribute <logrecord-attributes>` in.
            If :data:`None` then uses the ISO 8601 format ``'%Y-%m-%dT%H:%M:%S.%f'``.
        **kwargs
            Additional keyword arguments are passed to :class:`~msl.io.dataset.Dataset`.
            The default behaviour is to append every :ref:`logging record <log-record>`
            to the :class:`~msl.io.dataset.Dataset`. This guarantees that the size of the
            :class:`~msl.io.dataset.Dataset` is equal to the number of
            :ref:`logging records <log-record>` that were added to it. However, this behaviour
            can decrease the performance if many :ref:`logging records <log-record>` are
            added often because a copy of the data in the :class:`~msl.io.dataset.Dataset` is
            created for each :ref:`logging record <log-record>` that is added. You can improve
            the performance by specifying an initial size of the :class:`~msl.io.dataset.Dataset`
            by including a `shape` or a `size` keyword argument. This will also automatically
            create additional empty rows in the :class:`~msl.io.dataset.Dataset`, that is
            proportional to the size of the :class:`~msl.io.dataset.Dataset`, if the size of the
            :class:`~msl.io.dataset.Dataset` needs to be increased. If you do this then you will
            want to call :meth:`~msl.io.dataset_logging.DatasetLogging.remove_empty_rows` before
            writing :class:`~msl.io.dataset_logging.DatasetLogging` to a file or interacting
            with the data in :class:`~msl.io.dataset_logging.DatasetLogging` to remove the
            extra rows that were created.

        Returns
        -------
        :class:`~msl.io.dataset_logging.DatasetLogging`
            The :class:`~msl.io.dataset_logging.DatasetLogging` that was created.

        Examples
        --------
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
        is_read_only, metadata = self._check(False, **kwargs)
        name, parent = self._create_ancestors(name, is_read_only)
        if attributes is None:
            # if the default attribute names are changed then update the `attributes`
            # description in the docstring of create_dataset_logging() and require_dataset_logging()
            attributes = ['asctime', 'levelname', 'name', 'message']
        if date_fmt is None:
            # if the default date_fmt is changed then update the `date_fmt`
            # description in the docstring of create_dataset_logging() and require_dataset_logging()
            date_fmt = '%Y-%m-%dT%H:%M:%S.%f'
        return DatasetLogging(name, parent, level=level, attributes=attributes,
                              logger=logger, date_fmt=date_fmt, **metadata)

    def require_dataset_logging(self, name, level='INFO', attributes=None, logger=None, date_fmt=None, **kwargs):
        """Require that a :class:`~msl.io.dataset.Dataset` exists for handling :mod:`logging` records.

        If the :class:`~msl.io.dataset_logging.DatasetLogging` exists then it will be returned
        if it does not exist then it is created.

        Automatically creates the ancestor :class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`, optional
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` or :class:`tuple` of :class:`str`, optional
            The :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
            If the :class:`~msl.io.dataset.Dataset` exists and if `attributes`
            are specified and they do not match those of the existing
            :class:`~msl.io.dataset.Dataset` then a :exc:`ValueError` is raised.
            If :data:`None` and the :class:`~msl.io.dataset.Dataset` does not exist
            then uses ``asctime``, ``levelname``, ``name``, and ``message``.
        logger : :class:`~logging.Logger`, optional
            The :class:`~logging.Logger` that the :class:`~msl.io.dataset_logging.DatasetLogging` object
            will be added to. If :data:`None` then it is added to the ``root`` :class:`~logging.Logger`.
        date_fmt : :class:`str`, optional
            The :class:`~datetime.datetime` :ref:`format code <strftime-strptime-behavior>`
            to use to represent the ``asctime`` :ref:`attribute <logrecord-attributes>` in.
            If :data:`None` then uses the ISO 8601 format ``'%Y-%m-%dT%H:%M:%S.%f'``.
        **kwargs
            Additional keyword arguments are passed to :class:`~msl.io.dataset.Dataset`.
            The default behaviour is to append every :ref:`logging record <log-record>`
            to the :class:`~msl.io.dataset.Dataset`. This guarantees that the size of the
            :class:`~msl.io.dataset.Dataset` is equal to the number of
            :ref:`logging records <log-record>` that were added to it. However, this behaviour
            can decrease the performance if many :ref:`logging records <log-record>` are
            added often because a copy of the data in the :class:`~msl.io.dataset.Dataset` is
            created for each :ref:`logging record <log-record>` that is added. You can improve
            the performance by specifying an initial size of the :class:`~msl.io.dataset.Dataset`
            by including a `shape` or a `size` keyword argument. This will also automatically
            create additional empty rows in the :class:`~msl.io.dataset.Dataset`, that is
            proportional to the size of the :class:`~msl.io.dataset.Dataset`, if the size of the
            :class:`~msl.io.dataset.Dataset` needs to be increased. If you do this then you will
            want to call :meth:`~msl.io.dataset_logging.DatasetLogging.remove_empty_rows` before
            writing :class:`~msl.io.dataset_logging.DatasetLogging` to a file or interacting
            with the data in :class:`~msl.io.dataset_logging.DatasetLogging` to remove the
            extra rows that were created.

        Returns
        -------
        :class:`~msl.io.dataset_logging.DatasetLogging`
            The :class:`~msl.io.dataset_logging.DatasetLogging` that was created or
            that already existed.
        """
        name = '/' + name.strip('/')
        dataset_name = name if self.parent is None else self.name + name
        for dataset in self.datasets():
            if dataset.name == dataset_name:
                if ('logging_level' not in dataset.metadata) or \
                        ('logging_level_name' not in dataset.metadata) or \
                        ('logging_date_format' not in dataset.metadata):
                    raise ValueError('The required Dataset was found but it is not used for logging')

                if attributes and (dataset.dtype.names != tuple(attributes)):
                    raise ValueError('The attribute names of the existing '
                                     'logging Dataset are {} which does not equal {}'
                                     .format(dataset.dtype.names, tuple(attributes)))

                if isinstance(dataset, DatasetLogging):
                    return dataset

                # replace the existing Dataset with a new DatasetLogging object
                meta = dataset.metadata.copy()
                data = dataset.data.copy()

                # remove the existing Dataset from its descendants, itself and its ancestors
                groups = tuple(self.descendants()) + (self,) + tuple(self.ancestors())
                for group in groups:
                    for dset in group.datasets():
                        if dset is dataset:
                            key = '/' + dset.name.lstrip(group.name)
                            del group._mapping[key]

                # temporarily make this Group not in read-only mode
                original_read_only_mode = bool(self._is_read_only)
                self._is_read_only = False
                kwargs.update(meta)
                dset = self.create_dataset_logging(name, level=level, attributes=data.dtype.names,
                                                   logger=logger, date_fmt=meta.logging_date_format,
                                                   data=data, **kwargs)
                self._is_read_only = original_read_only_mode
                return dset

        return self.create_dataset_logging(name, level=level, attributes=attributes,
                                           logger=logger, date_fmt=date_fmt, **kwargs)

    def remove(self, name):
        """Remove a :class:`Group` or a :class:`~msl.io.dataset.Dataset`.

        Parameters
        ----------
        name : :class:`str`
            The name of the :class:`Group` or :class:`~msl.io.dataset.Dataset` to remove.

        Returns
        -------
        :class:`Group`, :class:`~msl.io.dataset.Dataset` or :data:`None`
            The :class:`Group` or :class:`~msl.io.dataset.Dataset` that was
            removed or :data:`None` if there was no :class:`Group` or
            :class:`~msl.io.dataset.Dataset` with the specified `name`.
        """
        name = '/' + name.strip('/')
        return self.pop(name, None)

    def _check(self, is_read_only, **kwargs):
        self._raise_if_read_only()
        kwargs.pop('parent', None)
        if is_read_only is None:
            return self._is_read_only, kwargs
        return is_read_only, kwargs

    def _create_ancestors(self, name, is_read_only):
        # automatically create the ancestor Groups if they do not already exist
        names = name.strip('/').split('/')
        parent = self
        for n in names[:-1]:
            if n not in parent:
                parent = Group(n, parent, is_read_only)
            else:
                parent = parent[n]
        return names[-1], parent
