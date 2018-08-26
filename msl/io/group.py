"""
A :class:`Group` can contain sub-:class:`Group`\'s and/or :class:`~msl.io.dataset.Dataset`\'s.
"""
from .vertex import Vertex
from .dataset import Dataset


class Group(Vertex):

    def __init__(self, name, parent, is_read_only, **metadata):
        """A :class:`Group` can contain sub-:class:`Group`\'s and/or :class:`~msl.io.dataset.Dataset`\'s.

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
        return str(dict((key, str(value)) for key, value in self._mapping.items()))

    def __str__(self):
        ng = len(list(self.groups()))
        nd = len(list(self.datasets()))
        nm = len(self.metadata)
        return '<{} "{}" ({} groups, {} datasets, {} attributes)>'\
            .format(self.__class__.__name__, self._name, ng, nd, nm)

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
        Returns a generator of all :class:`~msl.io.dataset.Dataset`\'s that are
        contained within this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_dataset(obj):
                yield obj

    def groups(self):
        """
        Returns a generator of all sub-:class:`Group`\'s that are contained within
        this :class:`Group`.
        """
        for obj in self._mapping.values():
            if self.is_group(obj):
                yield obj

    def create_group(self, name, is_read_only=None, **metadata):
        """Create a new sub-:class:`Group`

        Parameters
        ----------
        name : :class:`str`
            The name of the new sub-:class:`Group`.
        is_read_only : :class:`bool`, optional
            Whether to create this sub-:class:`Group` in read-only mode.
            If :data:`None` then uses the mode for this :class:`Group`.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for this sub-:class:`Group`.

        Returns
        -------
        :class:`Group`
            The new sub-:class:`Group` that was created.
        """
        is_read_only, kws = self._check(is_read_only, **metadata)
        return Group(name, self, is_read_only, **kws)

    def create_dataset(self, name, is_read_only=None, **kwargs):
        """Create a new :class:`~msl.io.dataset.Dataset`.

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
        is_read_only, kws = self._check(is_read_only, **kwargs)
        return Dataset(name, self, is_read_only, **kws)

    def _check(self, is_read_only, **kwargs):
        self._raise_if_read_only()
        kwargs.pop('parent', None)
        if is_read_only is None:
            return self._is_read_only, kwargs
        return is_read_only, kwargs
