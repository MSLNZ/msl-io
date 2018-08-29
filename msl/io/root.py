"""
The root vertex in a rooted_, `directed graph`_.

.. _rooted: https://en.wikipedia.org/wiki/Rooted_graph
.. _directed graph: https://en.wikipedia.org/wiki/Directed_graph
"""
import os

from .group import Group


class Root(Group):

    def __init__(self, url, is_read_only, cls, **metadata):
        """The root vertex in a rooted_, `directed graph`_.

        Do not instantiate this class directly. Call the
        :meth:`~msl.io.reader.Reader.create_root` method in the
        :meth:`~msl.io.reader.Reader.read` method that your :meth:`~msl.io.reader.Reader`
        overrides.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        is_read_only : :class:`bool`
            Whether to open the file in read-only mode.
        cls : :class:`type`
            The :class:`~msl.io.reader.Reader` subclass that was used to read the data file.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for the :class:`Root`.
        """
        super(Group, self).__init__('/', None, is_read_only, **metadata)
        self._url = url
        self._class = cls

    def __repr__(self):
        b = os.path.basename(self._url)
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        return '<Root {!r} ({} groups, {} datasets, {} metadata)>'.format(b, g, d, m)

    @property
    def url(self):
        """:class:`str`: The location of a file on a local hard drive or on a network."""
        return self._url

    @property
    def reader_class(self):
        """The Reader class that was used to read the data file."""
        return self._class
