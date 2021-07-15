"""
General functions.
"""
import re
import os
import stat
import shutil
import hashlib
import logging
import subprocess
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
try:
    PermissionError
except NameError:
    PermissionError = OSError  # for Python 2.7
    FileExistsError = OSError

logger = logging.getLogger(__package__)

_readers = []

__all__ = (
    'checksum',
    'copy',
    'git_revision',
    'register',
    'remove_write_permissions',
    'search',
    'send_email',
)


def checksum(file, algorithm='sha256', chunk_size=65536, shake_length=256):
    """Get the checksum of a file.

    A checksum is a sequence of numbers and letters that act as a fingerprint
    for a file against which later comparisons can be made to detect errors or
    changes in the file. It can be used to verify the integrity of the data.

    Parameters
    ----------
    file : :term:`path-like <path-like object>` or :term:`file <file object>` object
        A file to get the checksum of.
    algorithm : :class:`str`, optional
        The hash algorithm to use to compute the checksum.
        See :mod:`hashlib` for more details.
    chunk_size : :class:`int`, optional
        The number of bytes to read at a time from the file. It is useful
        to tweak this parameter when reading a large file to improve performance.
    shake_length : :class:`int`, optional
        The digest length to use for the ``SHAKE`` algorithm. See
        :meth:`hashlib.shake.hexdigest` for more details.

    Returns
    -------
    :class:`str`
        The checksum containing only hexadecimal digits.
    """
    def read(fp):
        # read in chucks in case the file size is too large
        # to load it into RAM all at once
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            hash_cls.update(data)

    hash_cls = hashlib.new(algorithm)

    try:
        with open(file, 'rb') as f:
            read(f)
    except TypeError:
        if not hasattr(file, 'tell'):
            raise
        position = file.tell()
        read(file)
        file.seek(position)

    try:
        return hash_cls.hexdigest()
    except TypeError:
        return hash_cls.hexdigest(shake_length)


def copy(source, destination, overwrite=False, include_metadata=True):
    """Copy a file.

    Parameters
    ----------
    source : :term:`path-like object`
        The path to a file to copy.
    destination : :term:`path-like object`
        A directory to copy the file to or a full path (i.e., includes the basename).
        If the directory does not exist then it, and all intermediate directories,
        will be created.
    overwrite : :class:`bool`, optional
        Whether to overwrite the `destination` file if it already exists.
        If `destination` already exists and `overwrite` is :data:`False` then a
        :exc:`FileExistsError` is raised.
    include_metadata : :class:`bool`, optional
        Whether to also copy information such as the file permissions,
        latest access time and latest modification time with the file.

    Returns
    -------
    :class:`str`
        The path to where the file was copied.
    """
    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))
    else:
        dir_name = os.path.dirname(destination)
        if dir_name and not os.path.isdir(dir_name):
            os.makedirs(dir_name)

    if not overwrite and os.path.isfile(destination):
        raise FileExistsError('Will not overwrite {!r}'.format(destination))

    # TODO include the follow_symlinks kwarg to copyfile and copystat
    #  when dropping support for Python 2.7
    shutil.copyfile(source, destination)
    if include_metadata:
        shutil.copystat(source, destination)

    return destination


def register(reader_class):
    """Use as a decorator to register a :class:`~msl.io.base_io.Reader` subclass.

    See :ref:`io-create-reader` for an example on how to use @register decorator.

    Parameters
    ----------
    reader_class : :class:`~msl.io.base_io.Reader`
        A :class:`~msl.io.base_io.Reader` subclass.

    Returns
    -------
    :class:`~msl.io.base_io.Reader`
        The :class:`~msl.io.base_io.Reader`.
    """
    def append(cls):
        _readers.append(cls)
        logger.debug('registered {!r}'.format(cls))
        return cls
    return append(reader_class)


def search(folder, pattern=None, levels=0, regex_flags=0, exclude_folders=None,
           ignore_permission_error=True, ignore_hidden_folders=True, follow_symlinks=False):
    r"""Search for files starting from a root folder.

    Parameters
    ----------
    folder : :class:`str`
        The root folder to begin searching for files.
    pattern : :class:`str`, optional
        A regex string to use to filter the filenames. If :data:`None` then no
        filtering is applied and all files are yielded.

        Examples:

        * ``r'data'`` :math:`\rightarrow` find all files with the word ``data``
          in the filename

        * ``r'\.png$'`` :math:`\rightarrow` find all files with the extension ``.png``

        * ``r'\.jpe*g$'`` :math:`\rightarrow` find all files with the extension
          ``.jpeg`` or ``.jpg``

    levels : :class:`int`, optional
        The number of sub-folder levels to recursively search for files.
        If :data:`None` then search all sub-folders.
    regex_flags : :class:`int`, optional
        The flags to use to compile regex strings.
    exclude_folders : :class:`str` or :class:`list` of :class:`str`, optional
        The pattern of folder names to exclude from the search. Can be a regex
        string. If :data:`None` then include all folders in the search.

        Examples:

        * ``r'bin'`` :math:`\rightarrow` exclude all folders that contain the word ``bin``

        * ``r'^My'`` :math:`\rightarrow` exclude all folders that start with the letters ``My``

        * ``[r'bin', r'^My']`` which is equivalent to ``r'(bin|^My')`` :math:`\rightarrow` exclude
          all folders that contain the word ``bin`` or start with the letters ``My``

    ignore_permission_error : :class:`bool`, optional
        Whether to ignore :exc:`PermissionError` exceptions when reading
        the items within a folder.
    ignore_hidden_folders : :class:`bool`, optional
        Whether to ignore hidden folders from the search. A hidden folder
        starts with a ``.`` (a dot).
    follow_symlinks : :class:`bool`, optional
        Whether to search for files by following symbolic links.

    Yields
    ------
    :class:`str`
        The path to a file.
    """
    if levels is not None and levels < 0:
        return

    if ignore_hidden_folders and os.path.basename(folder).startswith('.'):
        logger.debug('ignore hidden folder %r', folder)
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
                logger.debug('excluding folder %r', folder)
                return
    else:
        ex_compiled = None

    if ignore_permission_error:
        try:
            names = os.listdir(folder)
        except PermissionError:
            logger.debug('permission error %r', folder)
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
            for item in search(path,
                               pattern=regex,
                               levels=None if levels is None else levels - 1,
                               regex_flags=regex_flags,
                               exclude_folders=ex_compiled,
                               ignore_permission_error=ignore_permission_error,
                               ignore_hidden_folders=ignore_hidden_folders,
                               follow_symlinks=follow_symlinks):
                yield item


def send_email(to, config, subject='', body='', frm=None):
    """Send an email.

    Parameters
    ----------
    to : :class:`str`
        Who do you want to send the email to? Can omit the ``@domain`` part
        if a ``domain`` key is specified in the `config` file.
    config : :class:`str`
        The path to the configuration file to use to send the email. A
        configuration file contains ``key=value`` pairs.

        The following ``keys`` must be defined:

        - ``host``: The name, or IP address, of the remote host
        - ``port``: The port number to connect to on the remote host

        The following ``keys`` are optional:

        - ``domain``: The domain part of the email address. Can start with ``@``
        - ``use_encryption``: True|Yes|1 or False|No|0 [default: No]
        - ``username``: The user name to authenticate with
        - ``password``: The password for the authentication

        .. warning::
            Since this information is specified in plain text in the configuration
            file you should set the file permissions provided by your operating
            system to ensure that your authentication credentials are safe.

    subject : :class:`str`, optional
        The text to include in the subject field.
    body : :class:`str`, optional
        The text to include in the body of the email.
    frm : :class:`str`, optional
        Who is sending the email? If not specified then equals the `to` value.
    """
    cfg = dict()
    with open(config, 'r') as fp:
        for line in fp:
            if line.startswith('#'):
                continue
            line_split = line.split('=')
            if len(line_split) > 1:
                cfg[line_split[0].lower().strip()] = line_split[1].strip()

    host, port = cfg.get('host'), cfg.get('port')
    if host is None or port is None:
        raise ValueError('You must specify the "host" and "port" in the config file')

    domain = cfg.get('domain')
    if domain is not None and not domain.startswith('@'):
        domain = '@' + domain

    if domain is not None and '@' not in to:
        to += domain

    if frm is None:
        frm = to
    elif domain is not None and '@' not in frm:
        frm += domain

    server = SMTP(host=host, port=int(port))

    if cfg.get('use_encryption', 'no').lower()[0] in ('t', 'y', '1'):
        server.ehlo()
        server.starttls()
        server.ehlo()

    username, password = cfg.get('username'), cfg.get('password')
    if username and password:
        server.login(username, password)

    msg = MIMEMultipart()
    msg['From'] = frm
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.close()


def get_basename(obj):
    """Get the :func:`~os.path.basename` of a file.

    Parameters
    ----------
    obj : :term:`path-like <path-like object>` or :term:`file-like <file object>`
        The object to get the :func:`~os.path.basename` of. If the object does not
        support the :func:`~os.path.basename` function then the
        :attr:`__name__ <definition.__name__>` of the `obj` is returned.

    Returns
    -------
    :class:`str`
        The basename of `obj`.
    """
    try:
        return os.path.basename(obj)
    except (TypeError, AttributeError):
        try:
            return os.path.basename(obj.name)
        except AttributeError:
            return obj.__class__.__name__


def git_revision(git_dir, short=False):
    """Get the SHA-1 hash value of the git revision.

    This function requires that git_ is installed and that it is
    available on ``PATH``.

    .. _git: https://git-scm.com/

    Parameters
    ----------
    git_dir : :class:`str`
        A directory that is under version control.
    short : :class:`bool`, optional
        Whether to return the shortened version of the SHA-1 hash value.

    Returns
    -------
    :class:`str` or :data:`None`
        The SHA-1 hash value of the currently checked-out commit.
        If `git_dir` is not a directory that is under version then
        returns :data:`None`.
    """
    cmd = ['git', 'rev-parse', 'HEAD']
    if short:
        cmd.insert(2, '--short')
    try:
        sha1 = subprocess.check_output(cmd, cwd=git_dir, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return None
    return sha1.strip().decode('ascii')


def remove_write_permissions(path):
    """Remove all write permissions of a file.

    On Windows, this function will set the file attribute to be read only.

    On linux and macOS the write permission is removed for the User,
    Group and Others. The read and execute permissions are preserved.

    Parameters
    ----------
    path : :term:`path-like object`
        The path to remove the write permissions of.
    """
    current_permissions = stat.S_IMODE(os.lstat(path).st_mode)
    disable_writing = ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
    os.chmod(path, current_permissions & disable_writing)
