"""
Base classes for all :class:`Reader`\\s. and :class:`Writer`\\s.
"""
import os
import codecs
import itertools

from .group import Group
from .constants import IS_PYTHON2
from .utils import get_basename


class Root(Group):

    def __init__(self, file, **metadata):
        """The root_ vertex in a tree_.

        .. _root: https://en.wikipedia.org/wiki/Tree_(graph_theory)#Rooted_tree
        .. _tree: https://en.wikipedia.org/wiki/Tree_(graph_theory)

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file object to associate with the :class:`~msl.io.base.Root`.
        **metadata
            Key-value pairs that can be used as :class:`~msl.io.metadata.Metadata`
            for the :class:`~msl.io.base.Root`.
        """
        super(Group, self).__init__('/', None, False, **metadata)
        self._file = file

    def __repr__(self):
        b = get_basename(self._file)
        g = len(list(self.groups()))
        d = len(list(self.datasets()))
        m = len(self.metadata)
        return '<{} {!r} ({} groups, {} datasets, {} metadata)>'.\
            format(self.__class__.__name__, b, g, d, m)

    @property
    def file(self):
        """:term:`path-like <path-like object>` or :term:`file-like <file object>`: The file
        object that is associated with the :class:`Root`."""
        return self._file

    def tree(self, indent=2):
        """A representation of the `tree structure`_ of all :class:`~msl.io.group.Group`\\s
        and :class:`~msl.io.dataset.Dataset`\\s that are in :class:`Root`.

        .. _tree structure: https://en.wikipedia.org/wiki/Tree_structure

        Parameters
        ----------
        indent : :class:`int`, optional
            The amount of indentation to add for each recursive level.

        Returns
        -------
        :class:`str`
            The `tree structure`_.
        """
        return repr(self) + '\n' + \
            '\n'.join(' ' * (indent * k.count('/')) + repr(v) for k, v in sorted(self.items()))


class Writer(Root):

    def __init__(self, file=None, **metadata):
        """
        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The file to write the data to. Can also be specified in the :meth:`write` method.
        **metadata
            Key-value pairs that are used as :class:`~msl.io.metadata.Metadata`
            of the :class:`~msl.io.base.Root`.
        """
        super(Writer, self).__init__(file, **metadata)
        self._context_kwargs = {}

    def set_root(self, root):
        """Set a new :class:`Root` for the :class:`Writer`.

        .. attention::
           This will clear the :class:`~msl.io.metadata.Metadata` of the :class:`Writer`
           and all :class:`~msl.io.group.Group`\\s and :class:`~msl.io.dataset.Dataset`\\s
           that the :class:`Writer` currently contains. The `file` that was specified when
           the :class:`Writer` was created does not change.

        Parameters
        ----------
        root : :class:`Root`
            The new :class:`Root` for the :class:`Writer`.
        """
        if not isinstance(root, Group):  # it is okay to pass in any Group object
            raise TypeError('Must pass in a Root object, got {!r}'.format(root))
        self.clear()
        self.metadata.clear()
        self.add_metadata(**root.metadata)
        if root:  # only do this if there are Groups and/or Datasets in the new root
            self.add_group('', root)

    def update_context_kwargs(self, **kwargs):
        """
        When a :class:`Writer` is used as a :ref:`context manager <with>` the
        :meth:`write` method is automatically called when exiting the
        :ref:`context manager <with>`. You can specify the keyword arguments
        that will be passed to the :meth:`write` method by calling
        :meth:`update_context_kwargs` with the appropriate key-value pairs
        before the :ref:`context manager <with>` exits. You can call this
        method multiple times since the key-value pairs get added to the
        underlying :class:`dict` (via :meth:`dict.update`) that contains
        all keyword arguments which are passed to the :meth:`write` method.
        """
        self._context_kwargs.update(**kwargs)

    def write(self, file=None, root=None, **kwargs):
        """Write to a file.

        .. important::
           You must override this method.

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The file to write the `root` to. If :data:`None` then uses the
            `file` value that was specified when the :class:`~msl.io.base.Writer`
            was instantiated.
        root : :class:`~msl.io.base.Root`, optional
            Write the `root` object in the file format of this :class:`~msl.io.base.Writer`.
            This is useful when converting between different file formats.
        **kwargs
            Additional key-value pairs to use when writing the file.
        """
        raise NotImplementedError

    def save(self, file=None, root=None, **kwargs):
        """Alias for :meth:`write`."""
        self.write(file=file, root=root, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # always write the Root to the file even if
        # an exception was raised in the context manager
        self.write(**self._context_kwargs)


class Reader(Root):

    def __init__(self, file):
        """
        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file to read.
        """
        super(Reader, self).__init__(file)

    @staticmethod
    def can_read(file, **kwargs):
        """Whether this :class:`~msl.io.base.Reader` can read the file specified by `file`.

        .. important::
           You must override this method.

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file to check whether the :class:`~msl.io.base.Reader` can read it.
        **kwargs
            Key-value pairs that the :class:`~msl.io.base.Reader` class may need
            when checking if it can read the `file`.

        Returns
        -------
        :class:`bool`
            Either :data:`True` (can read) or :data:`False` (cannot read).
        """
        return False

    def read(self, **kwargs):
        """Read the file.

        The file can be accessed by the :attr:`~msl.io.base.Root.file`
        property of the :class:`~msl.io.base.Reader`, i.e., ``self.file``

        .. important::
           You must override this method.

        Parameters
        ----------
        **kwargs
            Key-value pairs that the :class:`~msl.io.base.Reader` class may need
            when reading the file.
        """
        raise NotImplementedError

    @staticmethod
    def get_lines(file, *args, **kwargs):
        """Return lines from a file.

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file to read lines from.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The line(s) in the file to get.

            Examples:

            * ``get_lines(file)`` :math:`\\rightarrow` returns all lines

            * ``get_lines(file, 5)`` :math:`\\rightarrow` returns the first 5 lines

            * ``get_lines(file, -5)`` :math:`\\rightarrow` returns the last 5 lines

            * ``get_lines(file, 2, 4)`` :math:`\\rightarrow` returns lines 2, 3 and 4

            * ``get_lines(file, 4, -1)`` :math:`\\rightarrow` skips the first 3 lines
              and returns the rest

            * ``get_lines(file, 2, -2)`` :math:`\\rightarrow` skips the first and last
              lines and returns the rest

            * ``get_lines(file, -4, -2)`` :math:`\\rightarrow` returns the fourth-,
              third- and second-last lines

            * ``get_lines(file, 1, -1, 6)`` :math:`\\rightarrow` returns every sixth
              line in the file

        **kwargs

            * ``remove_empty_lines`` : :class:`bool`

              Whether to remove all empty lines. Default is :data:`False`.

            * ``encoding`` : :class:`str`

              The name of the encoding to use to decode the file. The default is ``'utf-8'``.

            * ``errors`` : :class:`str`

              An optional string that specifies how encoding errors are to be handled.
              Either ``'strict'`` or ``'ignore'``. The default is ``'strict'``.

        Returns
        -------
        :class:`list` of :class:`str`
            The lines from the file. Trailing whitespace is stripped from each line.
        """
        remove_empty_lines = kwargs.pop('remove_empty_lines', False)

        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'

        if IS_PYTHON2:
            opener = codecs.open  # this allows the encoding and errors kwargs to be used
        else:
            opener = open

        # want the "stop" line to be included
        if (len(args) > 1) and (args[1] is not None) and (args[1] < 0):
            if args[1] == -1:
                args = (args[0], None) + args[2:]
            else:
                args = (args[0],) + (args[1] + 1,) + args[2:]

        # want the "start" line to be included
        if (len(args) > 1) and (args[0] is not None) and (args[0] > 0):
            args = (args[0] - 1,) + args[1:]

        is_file_like = hasattr(file, 'tell')

        # itertools.islice does not support negative indices, but want to allow
        # getting the last "N" lines from a file.
        if any(val < 0 for val in args if val):
            def get(_file):
                return [line.rstrip() for line in _file.readlines()]

            if is_file_like:
                position = file.tell()
                lines = get(file)
                file.seek(position)
            else:
                with opener(file, 'r', **kwargs) as f:
                    lines = get(f)

            if len(args) == 1:
                lines = lines[args[0]:]
            elif len(args) == 2:
                lines = lines[args[0]:args[1]]
            else:
                lines = lines[args[0]:args[1]:args[2]]

        else:
            if not args:
                args = (None,)

            def get(_file):
                return [line.rstrip() for line in itertools.islice(_file, *args)]

            if is_file_like:
                position = file.tell()
                lines = get(file)
                file.seek(position)
            else:
                with opener(file, 'r', **kwargs) as f:
                    lines = get(f)

        if remove_empty_lines:
            return [line for line in lines if line]

        return lines

    @staticmethod
    def get_bytes(file, *args):
        """Return bytes from a file.

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file to read bytes from.
        *args : :class:`int` or :class:`tuple` of :class:`int`, optional
            The position(s) in the file to retrieve bytes from.

            Examples:

            * ``get_bytes(file)`` :math:`\\rightarrow` returns all bytes

            * ``get_bytes(file, 5)`` :math:`\\rightarrow` returns the first 5 bytes

            * ``get_bytes(file, -5)`` :math:`\\rightarrow` returns the last 5 bytes

            * ``get_bytes(file, 5, 10)`` :math:`\\rightarrow` returns bytes 5 through
              10 (inclusive)

            * ``get_bytes(file, 3, -1)`` :math:`\\rightarrow` skips the first 2 bytes
              and returns the rest

            * ``get_bytes(file, -8, -4)`` :math:`\\rightarrow` returns the eighth-
              through fourth-last bytes (inclusive)

            * ``get_bytes(file, 1, -1, 2)`` :math:`\\rightarrow` returns every other byte

        Returns
        -------
        :class:`bytes`
            The bytes from the file.
        """
        is_file_like = hasattr(file, 'tell')
        if is_file_like:
            position = file.tell()
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(position)
        else:
            try:
                size = os.path.getsize(file)
            except OSError:
                # A file on a mapped network drive can raise the following:
                #   [WinError 87] The parameter is incorrect
                # for Python 3.5, 3.6 and 3.7. Also, calling os.path.getsize
                # on a file on a mapped network drive could return 0
                # (without raising OSError) on Python 3.8 and 3.9, which is
                # why we set size=0 on an OSError
                size = 0

            if size == 0:
                with open(file, mode='rt') as fp:
                    fp.seek(0, os.SEEK_END)
                    size = fp.tell()

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

        if is_file_like:
            position = file.tell()
            _file = file
        else:
            _file = open(file, mode='rb')

        _file.seek(start)
        data = _file.read(max(0, stop - start))
        if step != 1:
            data = data[::step]

        if is_file_like:
            file.seek(position)
        else:
            _file.close()

        return data

    @staticmethod
    def get_extension(file):
        """Return the extension of the file.

        Parameters
        ----------
        file : :term:`path-like <path-like object>` or :term:`file-like <file object>`
            The file to get the extension of.

        Returns
        -------
        :class:`str`
            The extension, including the ``'.'``.
        """
        try:
            return os.path.splitext(file)[1]
        except (TypeError, AttributeError):
            try:
                return Reader.get_extension(file.name)
            except AttributeError:
                return ''
