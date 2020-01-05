"""
A :class:`Group` can contain sub-:class:`Group`\\s and/or :class:`~msl.io.dataset.Dataset`\\s.
"""
import os

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
        """
        Returns a generator of all :class:`~msl.io.dataset.Dataset`\\s that are
        contained within this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_dataset(obj):
                yield obj

    def groups(self):
        """
        Returns a generator of all sub-:class:`Group`\\s that are contained within
        this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_group(obj):
                yield obj

    def add_group(self, name, group):
        """Add a :class:`Group`.

        The data in the :class:`~msl.io.dataset.Dataset`\\s that are added will be copied.

        Parameters
        ----------
        name : :class:`str`
            The name of the new :class:`Group` that you are adding.
        group : :class:`Group`
            The :class:`Group` to add.
        """
        if not isinstance(group, Group):
            raise TypeError('Must pass in a Group object, got {!r}'.format(group))

        name = '/' + name.strip('/')

        if not group:  # no sub-Groups or Datasets, only add the Metadata
            self.create_group(name + group.name, **group.metadata)
            return

        for key, vertex in group.items():
            n = name + key
            if self.is_group(vertex):
                self.create_group(n, **vertex.metadata)
            else:  # must be a Dataset
                self.create_dataset(n, data=vertex.data.copy(), **vertex.metadata)

    def create_group(self, name, is_read_only=None, **metadata):
        """Create a new :class:`Group`.

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

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

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

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

    def create_dataset(self, name, is_read_only=None, **kwargs):
        """Create a new :class:`~msl.io.dataset.Dataset`.

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

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

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

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

    def create_dataset_logging(self, name, level='INFO', attributes=None, **metadata):
        """Create a :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` or :class:`tuple` of :class:`str`
            The :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
            If :data:`None` then uses ``asctime``, ``levelname``, ``name``, and ``message``.
        **metadata
            All other key-value pairs will be used as
            :class:`~msl.io.metadata.Metadata` for the :class:`~msl.io.dataset.Dataset`.

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
        >>> print(log_dset)
        array([(..., 'INFO', 'my_logger', 'hi'), (..., 'ERROR', 'my_logger', 'cannot do that!')],
              dtype=[('asctime', 'O'), ('levelname', 'O'), ('name', 'O'), ('message', 'O')])

        Get all ``ERROR`` :ref:`logging records <log-record>`

        >>> print(log_dset[ log_dset['levelname']=='ERROR' ])
        [(..., 'ERROR', 'my_logger', 'cannot do that!')]

        Stop the :class:`~msl.io.dataset_logging.DatasetLogging` object
        from receiving :ref:`logging records <log-record>`

        >>> log_dset.remove_handler()
        """
        is_read_only, metadata = self._check(False, **metadata)
        name, parent = self._create_ancestors(name, is_read_only)
        if attributes is None:
            # if the default attribute names are changed then update the `attributes`
            # description in the docstring of create_dataset_logging() and require_dataset_logging()
            attributes = ['asctime', 'levelname', 'name', 'message']
        return DatasetLogging(name, parent, level=level, attributes=attributes, **metadata)

    def require_dataset_logging(self, name, level='INFO', attributes=None, **metadata):
        """Require that a :class:`~msl.io.dataset.Dataset` exists for handling :mod:`logging` records.

        If the :class:`~msl.io.dataset_logging.DatasetLogging` exists then it will be returned
        if it does not exist then it is created.

        Automatically creates the sub-:class:`Group`\\s if they do not exist.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` or :class:`tuple` of :class:`str`
            The :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
            If :data:`None` then uses ``asctime``, ``levelname``, ``name``, and ``message``.
            If the :class:`~msl.io.dataset.Dataset` exists and if `attributes`
            are specified and they do not match those of the existing
            :class:`~msl.io.dataset.Dataset` then a :exc:`ValueError` is raised.
        **metadata
            All other key-value pairs will be used as
            :class:`~msl.io.metadata.Metadata` for the :class:`~msl.io.dataset.Dataset`.

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
                        ('logging_level_name' not in dataset.metadata):
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

                # remove the existing Dataset from the ancestors, itself and the descendants
                groups = tuple(self.get_ancestors()) + (self,) + tuple(self.groups())
                for group in groups:
                    for dset in group.datasets():
                        if dset is dataset:
                            key = '/' + dset.name.lstrip(group.name)
                            del group._mapping[key]

                # temporarily make this Group not in read-only mode
                original_read_only_mode = bool(self._is_read_only)
                self._is_read_only = False
                dset = self.create_dataset_logging(name, level=level, attributes=data.dtype.names, data=data, **meta)
                dset.add_metadata(**metadata)
                self._is_read_only = original_read_only_mode
                return dset

        return self.create_dataset_logging(name, level=level, attributes=attributes, **metadata)

    def remove(self, name):
        """Remove a :class:`Group` or a :class:`Dataset`.

        Parameters
        ----------
        name : :class:`str`
            The name of the :class:`Group` or :class:`Dataset` to remove.

        Returns
        -------
        :class:`Group`, :class:`Dataset` or :data:`None`
            The :class:`Group` or :class:`Dataset` that was removed or :data:`None`
            if there was no :class:`Group` or :class:`Dataset` with the specified `name`.
        """
        name = '/' + name.strip('/')
        obj = self.pop(name, None)
        if obj is not None:
            # then pop it from descendants as well
            dirname, basename = os.path.split(name)
            while dirname != '/':
                item = self[dirname].pop(basename, None)
                if item is not None:
                    assert item is obj
                basename = '{}/{}'.format(os.path.basename(dirname), basename)
                dirname = os.path.dirname(dirname)
        return obj

    def get_ancestors(self):
        """Get the ancestors of this :class:`Group`.

        Yields
        ------
        :class:`Group`
            The ancestors of this :class:`Group`.
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

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
