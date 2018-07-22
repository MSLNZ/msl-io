"""
Base class for all :class:`Reader`\'s.
"""
import os
import sys

from .root import Root


class Reader(object):

    def __init__(self, url, **kwargs):
        """Base class for all :class:`Reader`\'s.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        **kwargs
            Key-value pairs that may be required when reading the file.
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

    @staticmethod
    def get_lines(url, *args):
        """Return lines from the file.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The line(s) in the file to get.

            Examples:

            - ``get_lines(url)`` -> returns all lines
            - ``get_lines(url, 5)`` -> returns the first 5 lines
            - ``get_lines(url, -5)`` -> returns the last 5 lines
            - ``get_lines(url, 2, 4)`` -> returns lines 2, 3 and 4
            - ``get_lines(url, 4, -1)`` -> skips the first 3 lines and returns the rest
            - ``get_lines(url, 2, -2)`` -> skips the first and last lines and returns the rest
            - ``get_lines(url, -4, -2)`` > returns the fourth-, third- and second-last lines

        Returns
        -------
        :class:`list` of :class:`str`
            The lines from the file. The newline character is stripped from each line.
        """
        def get_all_lines():
            with open(url, 'r') as f:
                return f.read().split('\n')

        if not args:
            return get_all_lines()
        elif len(args) == 1:
            start, stop = None, args[0]
        else:
            start, stop = args[0], args[1]

        # if either `start` or `stop` is negative then we must read all lines anyways
        if (start and start < 0) or (stop and stop < 0):
            lines = get_all_lines()
            if start is None:
                return lines[stop:]
            if start > 0:
                start -= 1
            if stop == -1:
                stop = None
            elif stop is not None and stop < -1:
                stop += 1
            return lines[start:stop]

        if start == 0 and stop is None:
            return []

        if stop is None:
            stop = sys.maxsize

        if stop == 0:
            return []

        if start is None:
            start = 1

        with open(url, 'r') as fp:

            # skip lines until the `start` line
            i = 0
            while i < start:
                line = fp.readline()
                if not line:
                    return []  # EOF reached
                i += 1
            lines = [line.rstrip()]

            # read lines until the EOF or until the `stop` line
            while i < stop:
                line = fp.readline()
                if not line:
                    break
                lines.append(line.rstrip())
                i += 1

            return lines

    @staticmethod
    def get_bytes(url, *args):
        """Return bytes from the file.

        Parameters
        ----------
        url : :class:`str`
            The location of a file on a local hard drive or on a network.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The position(s) in the file to retrieve bytes from.

            Examples:

            - ``get_bytes(url)`` -> returns all bytes
            - ``get_bytes(url, 5)`` -> returns the first 5 bytes
            - ``get_bytes(url, -5)`` -> returns the last 5 bytes
            - ``get_bytes(url, 5, 10)`` -> returns bytes 5 through 10 (inclusive)
            - ``get_bytes(url, 3, -1)`` -> skips the first 2 bytes and returns the rest
            - ``get_bytes(url, -8, -4)`` -> returns the eighth- through fourth-last bytes (inclusive)

        Returns
        -------
        :class:`bytes`
            The bytes from the file.
        """
        n = os.path.getsize(url)

        if not args:
            start, stop = 0, None
        elif len(args) == 1:
            val = args[0]
            if val is None:
                start, stop = 0, None
            elif val < 0:
                start, stop = n + val, None
            else:
                start, stop = 0, val
        else:
            start, stop = args[0], args[1]
            if start is None:
                start = 0
            elif start > 0:
                start -= 1
            if stop == -1:
                stop = None
            elif stop is not None and stop < -1:
                stop += 1

        if start > n:
            return b''

        if start < 0:
            start = max(0, start + n)

        with open(url, 'rb') as fp:
            fp.seek(start)

            if stop is None:
                return fp.read()

            if stop < 0:
                stop += n

            return fp.read(max(0, stop - start))

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

    def read(self):
        """
        Read the file specified by :attr:`.url`.

        .. important::
            You must override this method.
        """
        raise NotImplementedError

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
        return Root(self.url, False, **metadata)
