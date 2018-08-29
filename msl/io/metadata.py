"""
Data about data.
"""
from collections import MutableMapping

from .dictionary import Dictionary


class Metadata(Dictionary):

    def __init__(self, is_read_only, vertex_name, **kwargs):
        """Data about data.

        Do not instantiate directly. A :class:`Metadata` object is created automatically
        when :meth:`~msl.io.group.Group.create_dataset` or :meth:`~msl.io.group.Group.create_group`
        is called.

        Parameters
        ----------
        is_read_only : :class:`bool`
            Whether :class:`Metadata` is to be accessed in read-only mode.
        vertex_name : :class:`str`
            The name of the :class:`~msl.io.vertex.Vertex` that :class:`Metadata` is associated with.
        **kwargs
            Key-value pairs that will be used to create the :class:`.Dictionary`.
        """
        super(Metadata, self).__init__(is_read_only, **kwargs)
        self._vertex_name = vertex_name

    def __repr__(self):
        return '<Metadata {!r} {}>'.format(self._vertex_name, super(Metadata, self).__repr__())

    def __getitem__(self, item):
        try:
            value = self._mapping[item]
        except KeyError:
            pass  # raise a more detailed error message below
        else:
            if isinstance(value, MutableMapping):
                return Metadata(self._is_read_only, self._vertex_name, **value)
            return value
        self._raise_key_error(item)

    def __delattr__(self, item):
        self._raise_if_read_only()
        try:
            del self._mapping[item]
            return
        except KeyError as e:
            msg = str(e)
        raise AttributeError(msg)

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError as e:
            msg = str(e)
        raise AttributeError(msg)

    def __setattr__(self, item, value):
        if item.endswith('is_read_only'):
            super(Metadata, self).__setattr__('_is_read_only', bool(value))
        elif item == '_mapping' or item == '_vertex_name':
            super(Metadata, self).__setattr__(item, value)
        else:
            self._raise_if_read_only()
            self._mapping[item] = value

    def copy(self, is_read_only=None):
        """Create a copy of the :class:`Metadata`.

        Parameters
        ----------
        is_read_only : :class:`bool`, optional
            Whether the copy should be created in read-only mode. If :data:`None` then
            creates a copy using the mode for the :class:`Metadata` that is being copied.

        Returns
        -------
        :class:`Metadata`
            A copy of the :class:`Metadata`.
        """
        return Metadata(self._mode(is_read_only), self._vertex_name, **self._mapping)

    def fromkeys(self, seq, value=None, is_read_only=None):
        """Create a new :class:`Metadata` object with keys from `seq` and values set to `value`.

        Parameters
        ----------
        seq
            Any iterable object that contains the names of the keys.
        value : :class:`object`, optional
            The default value to use for each key.
        is_read_only : :class:`bool`, optional
            Whether the returned object should be created in read-only mode. If
            :data:`None` then uses the mode for the :class:`Metadata` that is used
            to call this method.

        Returns
        -------
        :class:`Metadata`
            A new :class:`Metadata` object.
        """
        return Metadata(self._mode(is_read_only), self._vertex_name, **dict((key, value) for key in seq))

    def _mode(self, is_read_only):
        return self._is_read_only if is_read_only is None else is_read_only
