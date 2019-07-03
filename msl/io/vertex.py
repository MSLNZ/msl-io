"""
A vertex in a `directed graph`_.

.. _directed graph: https://en.wikipedia.org/wiki/Directed_graph
"""
from .dictionary import Dictionary
from .metadata import Metadata


class Vertex(Dictionary):

    def __init__(self, name, parent, is_read_only, **metadata):
        """A vertex in a `directed graph`_.

        Parameters
        ----------
        name : :class:`str`
            The name of this vertex.
        parent : :class:`~msl.io.group.Group`
            The parent of this vertex.
        is_read_only : :class:`bool`
            Whether this vertex is in read-only mode.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for this :class:`Vertex`.
        """
        super(Vertex, self).__init__(is_read_only)

        if name is None:
            raise ValueError('The vertex name cannot be None')

        if parent is not None:
            # the name cannot contain '/' or '.' since these are special characters
            name = name.replace('/', '').replace('.', '')

            if not name:
                raise ValueError('The vertex name must be a non-empty string')

            # use a path name similar to a UNIX file system
            if parent.name.endswith('/'):
                name = parent.name + name
            else:
                name = parent.name + '/' + name

            # notify all ancestors that this vertex was created
            i = 0
            ancestor = parent
            name_split = name.split('/')
            while ancestor is not None:
                i += 1
                key = '/' + '/'.join(name_split[-i:])
                if key in ancestor._mapping:
                    raise ValueError('The name of this vertex, {!r}, is not unique'.format(key))
                ancestor._mapping[key] = self
                ancestor = ancestor._parent

        self._name = name
        self._parent = parent
        self._metadata = Metadata(is_read_only, name, **metadata)

    def __delitem__(self, item):
        self._raise_if_read_only()
        if item and not item[0] == '/':
            item = '/' + item

        try:
            del self._mapping[item]
        except KeyError:
            pass  # raise a more detailed error message below
        else:
            # delete all sub-vertices
            for key in list(self.keys()):
                if key.startswith(item):
                    del self._mapping[key]

            # notify all ancestors that this vertex was deleted
            ancestor = self._parent
            while ancestor is not None:
                for key in list(ancestor.keys()):
                    if key.endswith(item):
                        del ancestor._mapping[key]
                ancestor = ancestor._parent

            return

        self._raise_key_error(item)

    @property
    def is_read_only(self):
        """:class:`bool`: Whether this :class:`Vertex` is in read-only mode.

        Setting this value will also update all sub-:class:`~msl.io.group.Group`\\s
        and sub-:class:`~msl.io.dataset.Dataset`\\s to be in the same mode.
        """
        return self._is_read_only

    @is_read_only.setter
    def is_read_only(self, value):
        val = bool(value)

        self._is_read_only = val
        self._metadata.is_read_only = val

        # update all descendants of this vertex
        for obj in self._mapping.values():
            obj.is_read_only = val

    @property
    def name(self):
        """:class:`str`: The name of this :class:`Vertex`."""
        return self._name

    @property
    def parent(self):
        """:class:`~msl.io.group.Group`: The parent of this :class:`Vertex`."""
        return self._parent

    @property
    def metadata(self):
        """:class:`~msl.io.metadata.Metadata`: The metadata associated with this :class:`Vertex`."""
        return self._metadata

    def add_metadata(self, **metadata):
        """Add key-value pairs to the :class:`~msl.io.metadata.Metadata` for this :class:`Vertex`."""
        self._metadata.update(**metadata)
