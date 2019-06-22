"""
Base class for all :class:`Reader`\'s.
"""
import os
import itertools

from .root import Root


class Reader(object):

    def __init__(self, url, **kwargs):
        """Base class for all :class:`Reader`\'s.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        **kwargs
            Key-value pairs that a :class:`Reader` subclass may need when reading the file.
        """
        self._url = url

    @property
    def url(self):
        """:class:`str`: The location of a file on a local hard drive or on a network."""
        return self._url

    @staticmethod
    def can_read(url):
        """:class:`bool`: Whether this :class:`Reader` can read the file specified by `url`.

        .. important::
            You must override this method.
        """
        return False

    def create_root(self, **metadata):
        """Create the :class:`~msl.io.root.Root` :class:`~msl.io.group.Group`.

        Parameters
        ----------
        **metadata
            Key-value pairs that are used to create the :class:`~msl.io.metadata.Metadata`
            for the :class:`~msl.io.root.Root`.

        Returns
        -------
        :class:`~msl.io.root.Root`
            The root :class:`~msl.io.group.Group`, in writeable mode.
        """
        return Root(self._url, False, self.__class__, **metadata)

    def read(self):
        """
        Read the file specified by :attr:`.url`.

        .. important::
            You must override this method, for example:

            .. code-block:: python

                def read(self):
                    # read the data, for example, from a text-based file
                    lines = self.get_lines(self.url)

                    # create the root object (with optional metadata)
                    root = self.create_root(**metadata)

                    # ... create the Groups and Datasets ...

                    # return the root object
                    return root

        """
        raise NotImplementedError

    @staticmethod
    def get_lines(url, *args, **kwargs):
        """Return lines from a file.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The line(s) in the file to get.

            Examples:

            * ``get_lines(url)`` :math:`\\rightarrow` returns all lines

            * ``get_lines(url, 5)`` :math:`\\rightarrow` returns the first 5 lines

            * ``get_lines(url, -5)`` :math:`\\rightarrow` returns the last 5 lines

            * ``get_lines(url, 2, 4)`` :math:`\\rightarrow` returns lines 2, 3 and 4

            * ``get_lines(url, 4, -1)`` :math:`\\rightarrow` skips the first 3 lines
              and returns the rest

            * ``get_lines(url, 2, -2)`` :math:`\\rightarrow` skips the first and last
              lines and returns the rest

            * ``get_lines(url, -4, -2)`` :math:`\\rightarrow` returns the fourth-,
              third- and second-last lines

            * ``get_lines(url, 1, -1, 6)`` :math:`\\rightarrow` returns every sixth
              line in the file

        **kwargs
            Accepts the following:

            * ``remove_empty_lines`` : :class:`bool`, default: :data:`False`

              Whether to remove all empty lines.

        Returns
        -------
        :class:`list` of :class:`str`
            The lines from the file. Trailing whitespace is stripped from each line.
        """

        # want the "stop" line to be included
        if (len(args) > 1) and (args[1] is not None) and (args[1] < 0):
            if args[1] == -1:
                args = (args[0], None) + args[2:]
            else:
                args = (args[0],) + (args[1] + 1,) + args[2:]

        # want the "start" line to be included
        if (len(args) > 1) and (args[0] is not None) and (args[0] > 0):
            args = (args[0] - 1,) + args[1:]

        # itertools.islice does not support negative indices, but want to allow
        # getting the last "N" lines from a file.
        if any(val < 0 for val in args if val):
            with open(url, 'r') as f:
                lines = [line.rstrip() for line in f.readlines()]

            if len(args) == 1:
                lines = lines[args[0]:]
            elif len(args) == 2:
                lines = lines[args[0]:args[1]]
            else:
                lines = lines[args[0]:args[1]:args[2]]

        else:
            if not args:
                args = (None,)

            with open(url, 'r') as f:
                lines = [line.rstrip() for line in itertools.islice(f, *args)]

        if kwargs.get('remove_empty_lines', False):
            return [line for line in lines if line]

        return lines

    @staticmethod
    def get_bytes(url, *args):
        """Return bytes from a file.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The position(s) in the file to retrieve bytes from.

            Examples:

            * ``get_bytes(url)`` :math:`\\rightarrow` returns all bytes

            * ``get_bytes(url, 5)`` :math:`\\rightarrow` returns the first 5 bytes

            * ``get_bytes(url, -5)`` :math:`\\rightarrow` returns the last 5 bytes

            * ``get_bytes(url, 5, 10)`` :math:`\\rightarrow` returns bytes 5 through
              10 (inclusive)

            * ``get_bytes(url, 3, -1)`` :math:`\\rightarrow` skips the first 2 bytes
              and returns the rest

            * ``get_bytes(url, -8, -4)`` :math:`\\rightarrow` returns the eighth-
              through fourth-last bytes (inclusive)

            * ``get_bytes(url, 1, -1, 2)`` :math:`\\rightarrow` returns every other byte

        Returns
        -------
        :class:`bytes`
            The bytes from the file.
        """
        size = os.path.getsize(url)

        if not args:
            start, stop, step = 0, size, 1
        elif len(args) == 1:
            start, stop, step = 0, args[0], 1
            if stop is None:
                stop = size
            elif stop < 0:
                start, stop = size + stop + 1, size
        elif len(args) == 2:
            start, stop, step = args[0] or 0, args[1], 1
            if stop is None or stop == -1:
                stop = size
        else:
            start, stop, step = args[0] or 0, args[1] or size, args[2] or 1

        if start < 0:
            start = max(size + start, 0)
        elif start > 0:
            start -= 1
        start = min(size, start)

        if stop < 0:
            stop += size + 1
        stop = min(size, stop)

        with open(url, 'rb') as f:
            f.seek(start)
            data = f.read(max(0, stop - start))
            if step == 1:
                return data
            return data[::step]

    @staticmethod
    def get_extension(url):
        """Return the extension of the file.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.

        Returns
        -------
        :class:`str`
            The extension, including the ``"."``.
        """
        return os.path.splitext(url)[1]
