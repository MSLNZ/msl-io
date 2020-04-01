"""
A vertex in a tree_.

.. _tree: https://en.wikipedia.org/wiki/Tree_(graph_theory)
"""
import os

from .dictionary import Dictionary
from .metadata import Metadata


class Vertex(Dictionary):

    def __init__(self, name, parent, is_read_only, **metadata):
        """A vertex in a tree_.

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
            for this :class:`~msl.io.vertex.Vertex`.
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
            popped = self._mapping.pop(item)
        except KeyError:
            pass  # raise a more detailed error message below
        else:

            # use recursion to delete the reference to
            # `popped` from the head of this Vertex
            head, tail = os.path.split(item)
            if head != '/':
                assert self[head].pop(tail) is popped

            def notify_ancestors(obj):
                # delete all references to `obj` from the
                # ancestors of this Vertex
                ancestor = self._parent
                while ancestor is not None:
                    for k, v in list(ancestor.items()):
                        if obj is v:
                            del ancestor._mapping[k]
                    ancestor = ancestor._parent

            notify_ancestors(popped)

            # delete all descendant of this Vertex
            # (this is necessary if the popped item is a Group)
            for name, vertex in list(self.items()):
                if vertex.name.startswith(popped.name):
                    vertex = self._mapping.pop(name)
                    notify_ancestors(vertex)

            return

        self._raise_key_error(item)

    @property
    def is_read_only(self):
        """:class:`bool`: Whether this :class:`~msl.io.vertex.Vertex` is in read-only mode.

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
        """:class:`str`: The name of this :class:`~msl.io.vertex.Vertex`."""
        return self._name

    @property
    def parent(self):
        """:class:`~msl.io.group.Group`: The parent of this :class:`~msl.io.vertex.Vertex`."""
        return self._parent

    @property
    def metadata(self):
        """:class:`~msl.io.metadata.Metadata`: The metadata associated with this :class:`~msl.io.vertex.Vertex`."""
        return self._metadata

    def add_metadata(self, **metadata):
        """Add key-value pairs to the :class:`~msl.io.metadata.Metadata` for this :class:`~msl.io.vertex.Vertex`."""
        self._metadata.update(**metadata)
