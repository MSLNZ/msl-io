"""
A :class:`Group` can contain sub-:class:`Group`\\s and/or :class:`~msl.io.dataset.Dataset`\\s.
"""
from .vertex import Vertex
from .dataset import Dataset


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

    def create_group(self, name, is_read_only=None, **metadata):
        """Create a new :class:`Group`

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
        if name.endswith('/'):
            name = name[:-1]
        if not name.startswith('/'):
            name = '/' + name
        for group in self.groups():
            if group.name == name:
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
        if name.endswith('/'):
            name = name[:-1]
        if not name.startswith('/'):
            name = '/' + name
        for dataset in self.datasets():
            if dataset.name == name:
                if is_read_only is not None:
                    dataset.is_read_only = is_read_only
                if kwargs:  # only add the kwargs that should be Metadata
                    for kw in ['shape', 'dtype', 'buffer', 'offset', 'strides', 'order', 'data']:
                        kwargs.pop(kw, None)
                dataset.add_metadata(**kwargs)
                return dataset
        return self.create_dataset(name, is_read_only=is_read_only, **kwargs)

    def _check(self, is_read_only, **kwargs):
        self._raise_if_read_only()
        kwargs.pop('parent', None)
        if is_read_only is None:
            return self._is_read_only, kwargs
        return is_read_only, kwargs

    def _create_ancestors(self, name, is_read_only):
        # automatically create the ancestor Groups if they do not already exist
        if name.endswith('/'):
            name = name[:-1]
        if name.startswith('/'):
            name = name[1:]

        names = name.split('/')
        parent = self
        for n in names[:-1]:
            if n not in parent:
                parent = Group(n, parent, is_read_only)
            else:
                parent = parent[n]
        return names[-1], parent
