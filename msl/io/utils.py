"""
General functions.
"""
import re
import os
import logging

logger = logging.getLogger(__name__)

try:
    PermissionError
except NameError:
    PermissionError = OSError  # for Python 2.7


def find_files(folder, pattern=None, levels=0, regex_flags=0, exclude_folders=None,
               ignore_permission_error=True, ignore_hidden_folders=True, follow_symlinks=False):
    """Search for files starting from a base folder.

    Parameters
    ----------
    folder : :class:`str`
        The base folder to begin searching for files.
    pattern : :class:`str`, optional
        A regex string to use to filter the filenames. If :data:`None` then no
        filtering is applied and all files are yielded.

        Examples,

        * ``'data'`` -> find all files with the word ``data`` in the filename
        * ``'\.png$'`` -> find all files with the extension ``png``
        * ``'\.jpe*g$'`` -> find all files with the extensions ``jpeg`` and ``jpg``

    levels : :class:`int`, optional
        The number of sub-folder levels to recursively search for files.
        If :data:`None` then search all sub-folders.
    regex_flags : :class:`int`, optional
        The flags to use to compile regex strings.
    exclude_folders : :class:`str` or :class:`list` of :class:`str`, optional
        The pattern of folder names to exclude from the search. Can be a regex
        string. If :data:`None` then include all folders in the search.

        Examples,

        * ``'bin'`` -> exclude all folders that contain the word ``bin``
        * ``'^My'`` -> exclude all folders that start with the letters ``My``
        * ``['bin', '^My']`` or ``'(bin|^My')`` -> exclude all folders that contain
          the word ``bin`` and start with the letters ``My``

    ignore_permission_error : :class:`bool`, optional
        Whether to ignore :exc:`PermissionError` exceptions when reading
        the items within a folder.
    ignore_hidden_folders : :class:`bool`, optional
        Whether to ignore hidden folders from the search. A hidden folder
        starts with a ``.``.
    follow_symlinks : :class:`bool`, optional
        Whether to search for files by following symbolic links.

    Yields
    ------
    :class:`str`
        The path to a file.
    """
    if levels is not None and levels < 0:
        logger.debug('find_files -> passed lowest-level folder %r', folder)
        return

    if ignore_hidden_folders and os.path.basename(folder).startswith('.'):
        logger.debug('find_files -> ignore hidden folder %r', folder)
        return

    if exclude_folders:
        if isinstance(exclude_folders, str):
            exclude_folders = [exclude_folders]

        if isinstance(exclude_folders[0], str):
            ex_compiled = [re.compile(ex, flags=regex_flags) for ex in exclude_folders]
        else:  # the items should already be of type re.Pattern
            ex_compiled = exclude_folders

        basename = os.path.basename(folder)
        for exclude in ex_compiled:
            if exclude.search(basename):
                logger.debug('find_files -> excluding folder %r', folder)
                return
    else:
        ex_compiled = None

    if ignore_permission_error:
        try:
            names = os.listdir(folder)
        except PermissionError:
            logger.debug('find_files -> permission error %r', folder)
            return
    else:
        names = os.listdir(folder)

    if isinstance(pattern, str):
        regex = re.compile(pattern, flags=regex_flags) if pattern else None
    else:  # the value should already be of type re.Pattern
        regex = pattern

    for name in names:
        path = folder + '/' + name
        if os.path.isfile(path):
            if regex is None or regex.search(name):
                yield path
        elif os.path.isdir(path) or (follow_symlinks and os.path.islink(path)):
            for item in find_files(path,
                                   pattern=regex,
                                   levels=None if levels is None else levels - 1,
                                   regex_flags=regex_flags,
                                   exclude_folders=ex_compiled,
                                   ignore_permission_error=ignore_permission_error,
                                   ignore_hidden_folders=ignore_hidden_folders,
                                   follow_symlinks=follow_symlinks):
                yield item
