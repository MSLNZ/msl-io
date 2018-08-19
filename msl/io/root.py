"""
The root vertex in a rooted_, `directed graph`_.

.. _rooted: https://en.wikipedia.org/wiki/Rooted_graph
.. _directed graph: https://en.wikipedia.org/wiki/Directed_graph
"""
from .group import Group


class Root(Group):

    def __init__(self, url, is_read_only, **metadata):
        """The root vertex in a rooted_, `directed graph`_.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        is_read_only : :class:`bool`
            Whether to open the file in read-only mode.
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for the :class:`Root`.
        """
        super(Group, self).__init__('/', None, is_read_only, **metadata)
        self._url = str(url)

    def __str__(self):
        return '<{} id={:#x} url={}>'.format(self.__class__.__name__, id(self), self._url)

    @property
    def url(self):
        """:class:`str`: The location of a file on a local hard drive or on a network."""
        return self._url
