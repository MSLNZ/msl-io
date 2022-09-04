"""
General functions.
"""
import re
import os
import sys
import stat
import ctypes
import shutil
import hashlib
import logging
import subprocess
from smtplib import SMTP
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from configparser import ConfigParser
try:
    PermissionError
except NameError:
    PermissionError = OSError  # for Python 2.7
    FileExistsError = OSError

logger = logging.getLogger(__package__)

_readers = []


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
        with open(file, mode='rb') as f:
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
    if os.path.isdir(destination) or is_dir_accessible(destination):
        destination = os.path.join(destination, os.path.basename(source))
    else:
        # TODO include the exist_ok kwarg to makedirs
        #  when dropping support for Python 2.7
        try:
            os.makedirs(os.path.dirname(destination))
        except OSError:
            pass

    if not overwrite and (os.path.isfile(destination) or is_file_readable(destination)):
        raise FileExistsError('Will not overwrite {!r}'.format(destination))

    # TODO include the follow_symlinks kwarg to copyfile and copystat
    #  (and to this "copy" function) when dropping support for Python 2.7
    shutil.copyfile(source, destination)
    if include_metadata:
        shutil.copystat(source, destination)

    return destination


def is_admin():
    """Check if the current process is being run as an administrator.

    Returns
    -------
    :class:`bool`
        Whether the current process is being run as an administrator.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except AttributeError:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False


def is_dir_accessible(path, strict=False):
    """Check if a directory exists and is accessible.

    An accessible directory is one that the user has
    permission to access.

    Parameters
    ----------
    path : :class:`str`
        The directory to check.
    strict : :class:`bool`, optional
        Whether to raise the exception (if one occurs).

    Returns
    -------
    :class:`bool`
        Whether the directory exists and is accessible.
    """
    cwd = os.getcwd()
    try:
        os.chdir(path)
    except:
        if strict:
            raise
        return False
    else:
        os.chdir(cwd)
        return True


def is_file_readable(file, strict=False):
    """Check if a file exists and is readable.

    Parameters
    ----------
    file : :class:`str`
        The file to check.
    strict : :class:`bool`, optional
        Whether to raise the exception (if one occurs).

    Returns
    -------
    :class:`bool`
        Whether the file exists and is readable.
    """
    try:
        with open(file, mode='rb'):
            return True
    except:
        if strict:
            raise
        return False


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
        logger.debug('registered %r', cls)
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
        filtering is applied and all files are yielded. Examples:

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
        string. If :data:`None` then include all folders in the search. Examples:

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
        if os.path.isfile(path) or is_file_readable(path):
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


def send_email(config, recipient, sender=None, subject=None, body=None):
    """Send an email.

    Parameters
    ----------
    config : :class:`str`
        The path to an INI-style configuration file that contains information
        on how to send the email. There are two ways to send an email

        * Gmail API
        * SMTP server

        An example INI file for using the Gmail API is the following
        (see :class:`~msl.io.google_api.GMail` for more details)

        .. code-block:: ini

           [gmail]
           account = work [default: None]
           credentials = path/to/client_secrets.json [default: None]
           scopes =       [default: None]
             https://www.googleapis.com/auth/gmail.send
             https://www.googleapis.com/auth/gmail.metadata
           domain = @gmail.com [default: None]

        An example INI file for an SMTP server is the following

        .. code-block:: ini

           [smtp]
           host = hostname or IP address of the SMTP server
           port = port number to connect to on the SMTP server
           starttls = true|yes|1|on -or- false|no|0|off [default: false]
           username = the username to authenticate with [default: None]
           password = the password for username [default: None]
           domain = @company.com [default: None]

        .. warning::
            Since this information is specified in plain text in the configuration
            file you should set the file permissions provided by your operating
            system to ensure that your authentication credentials are safe.

    recipient : :class:`str`
        The email address of the recipient. Can omit the ``@domain.com`` part
        if a ``domain`` key is specified in the `config` file. Can be the
        value ``'me'`` if sending an email to yourself via Gmail.
    sender : :class:`str`, optional
        The email address of the sender. Can omit the ``@domain.com`` part
        if a ``domain`` key is specified in the `config` file. If not
        specified then it equals the value of the `recipient` parameter if
        using SMTP or the value ``'me'`` if using Gmail.
    subject : :class:`str`, optional
        The text to include in the subject field.
    body : :class:`str`, optional
        The text to include in the body of the email.
    """
    cfg = _prepare_email(config, recipient, sender)
    if cfg['type'] == 'smtp':
        server = SMTP(host=cfg['host'], port=cfg['port'])
        if cfg['starttls']:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if cfg['username'] and cfg['password']:
            server.login(cfg['username'], cfg['password'])
        msg = MIMEMultipart()
        msg['From'] = cfg['from']
        msg['To'] = cfg['to']
        msg['Subject'] = subject or '(no subject)'
        msg.attach(MIMEText(body or '', 'plain'))
        server.sendmail(cfg['from'], cfg['to'], msg.as_string())
        server.close()
    else:
        # import here since installing the Google-API packages is optional
        from .google_api import GMail
        gmail = GMail(account=cfg['account'], credentials=cfg['credentials'], scopes=cfg['scopes'])
        gmail.send(cfg['to'], sender=cfg['from'], subject=subject, body=body)


def _prepare_email(config, to, frm):
    """Loads a configuration file to prepare for sending an email.

    Returns a dict.
    """
    # opening the file makes sure that it exists since
    # ConfigParser().read() will silently ignore FileNotFoundError
    cp = ConfigParser()
    with open(config, mode='rt') as fp:
        cp.read_string(fp.read())

    has_smtp = cp.has_section('smtp')
    has_gmail = cp.has_section('gmail')
    if has_smtp and has_gmail:
        raise ValueError("Cannot specify both a 'gmail' and 'smtp' section")
    if not (has_smtp or has_gmail):
        raise ValueError("Must create either a 'gmail' or 'smtp' section")

    section = cp['gmail'] if has_gmail else cp['smtp']

    domain = section.get('domain')
    if domain and not domain.startswith('@'):
        domain = '@' + domain

    if domain and '@' not in to:
        to += domain

    if not frm:
        if has_gmail:
            frm = 'me'
        else:
            frm = to
    elif domain and ('@' not in frm) and (has_smtp or (has_gmail and frm != 'me')):
        frm += domain

    cfg = {'type': section.name, 'to': to, 'from': frm}
    if has_smtp:
        host, port = section.get('host'), section.getint('port')
        if not (host and port):
            raise ValueError("Must specify the 'host' and 'port' of the SMTP server")

        username, password = section.get('username'), section.get('password')
        if username and not password:
            raise ValueError("Must specify the 'password' since a "
                             "'username' is specified")
        elif password and not username:
            raise ValueError("Must specify the 'username' since a "
                             "'password' is specified")

        cfg.update({
            'host': host,
            'port': port,
            'starttls': section.getboolean('starttls'),
            'username': username,
            'password': password,
        })
    else:
        scopes = section.get('scopes')
        cfg.update({
            'account': section.get('account'),
            'credentials': section.get('credentials'),
            'scopes': scopes.split() if scopes else None
        })
    return cfg


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


def git_head(directory):
    """Get information about the ``HEAD`` of a repository.

    This function requires that `git <https://git-scm.com/>`_ is installed
    and that it is available on ``PATH``.

    Parameters
    ----------
    directory : :class:`str`
        A directory that is under version control.

    Returns
    -------
    :class:`dict` or :data:`None`
        Information about the most recent commit on the current branch.
        If `directory` is not a directory that is under version control
        then returns :data:`None`.
    """
    cmd = ['git', 'show', '-s', '--format=%H %ct', 'HEAD']
    try:
        out = subprocess.check_output(cmd, cwd=directory, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return None

    sha, timestamp = out.split()
    return {
        'hash': sha.decode('ascii'),
        'datetime': datetime.fromtimestamp(int(timestamp))
    }


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


def run_as_admin(args=None, executable=None, cwd=None, capture_stderr=False,
                 blocking=True, show=False, **kwargs):
    """Run a process as an administrator and return its output.

    Parameters
    ----------
    args : :class:`str` or :class:`list` of :class:`str`, optional
        A sequence of program arguments or else a single string. Providing a
        sequence of arguments is generally preferred, as it allows the module
        to take care of any required escaping and quoting of arguments
        (e.g., to permit spaces in file names).
    executable : :class:`str`, optional
        The executable to pass the `args` to.
    cwd : :class:`str`, optional
        The working directory for the elevated process.
    capture_stderr : :class:`bool`, optional
        Whether to send the stderr stream to stdout.
    blocking : :class:`bool`, optional
        Whether to wait for the process to finish before returning to the
        calling program.
    show : :class:`bool`, optional
        Whether to show the elevated console (Windows only). If
        :data:`True` then the stdout stream of the process is not captured.
    kwargs
        If the current process already has admin privileges or if the operating
        system is not Windows then all additional keyword arguments are passed
        to :func:`~subprocess.check_output`. Otherwise only a `timeout` keyword
        argument is used (Windows).

    Returns
    -------
    :class:`bytes`, :class:`int` or :class:`~subprocess.Popen`
        The returned object depends on whether the process is executed in blocking
        or non-blocking mode. If blocking then :class:`bytes` are returned (the
        stdout stream of the process). If non-blocking, then the returned object
        will either be the :class:`~subprocess.Popen` instance that is running the
        process (POSIX) or an :class:`int` which is the process ID (Windows).

    Examples
    --------
    .. invisible-code-block: pycon

       >>> SKIP_RUN_AS_ADMIN()

    Import the modules

    >>> import sys
    >>> from msl.io import run_as_admin

    Run a shell script

    >>> run_as_admin(['./script.sh', '--message', 'hello world'])

    Run a Python script

    >>> run_as_admin([sys.executable, 'script.py', '--verbose'], cwd='D:\\\\My Scripts')

    Create a service in the Windows registry and in the Service Control Manager database

    >>> run_as_admin(['sc', 'create', 'MyLogger', 'binPath=', 'C:\\\\logger.exe', 'start=', 'auto'])
    """
    if not args and not executable:
        raise ValueError('Must specify the args and/or an executable')

    stderr = subprocess.STDOUT if capture_stderr else None
    process = subprocess.check_output if blocking else subprocess.Popen

    if is_admin():
        return process(args, executable=executable, cwd=cwd,
                       stderr=stderr, **kwargs)

    if cwd is None:
        cwd = os.getcwd()

    if os.name != 'nt':
        if not args:
            command = ['sudo', executable]
        elif isinstance(args, str):
            exe = executable or ''
            command = 'sudo {} {}'.format(exe, args)
        else:
            exe = [executable] if executable else []
            command = ['sudo'] + exe + list(args)
        return process(command, cwd=cwd, stderr=stderr, **kwargs)

    # Windows is more complicated

    if args is None:
        args = ''

    if not isinstance(args, str):
        args = subprocess.list2cmdline(args)

    if executable is None:
        executable = ''
    else:
        executable = subprocess.list2cmdline([executable])

    # the 'runas' verb starts in C:\WINDOWS\system32
    cd = subprocess.list2cmdline(['cd', '/d', cwd, '&&'])

    # check if a Python environment needs to be activated
    activate = ''
    if executable == sys.executable or args.startswith(sys.executable):
        conda = os.getenv('CONDA_PREFIX')  # conda
        venv = os.getenv('VIRTUAL_ENV')  # venv
        if conda:
            env = os.getenv('CONDA_DEFAULT_ENV')
            assert env, 'CONDA_DEFAULT_ENV environment variable does not exist'
            if env == 'base':
                bat = os.path.join(conda, 'Scripts', 'activate.bat')
            else:
                bat = os.path.abspath(os.path.join(conda, os.pardir, os.pardir,
                                                   'Scripts', 'activate.bat'))
            assert os.path.isfile(bat), 'Cannot find {!r}'.format(bat)
            activate = subprocess.list2cmdline([bat, env, '&&'])
        elif venv:
            bat = os.path.join(venv, 'Scripts', 'activate.bat')
            assert os.path.isfile(bat), 'Cannot find {!r}'.format(bat)
            activate = subprocess.list2cmdline([bat, '&&'])

    # redirect stdout (stderr) to a file
    redirect = ''
    stdout_file = ''
    if not show:
        import uuid
        import tempfile
        stdout_file = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        r = ['>', stdout_file]
        if capture_stderr:
            r.append('2>&1')
        redirect = subprocess.list2cmdline(r)
        if re.search(r'\d$', args):
            # this number is also considered as a file handle, so add a space
            redirect = ' ' + redirect

    # the string that is passed to cmd.exe
    params = '/S /C "{cd} {activate} {executable} {args}"{redirect}'.format(
        cd=cd, activate=activate, executable=executable, args=args, redirect=redirect)

    from ctypes.wintypes import DWORD, ULONG, HWND, LPCWSTR, INT, HINSTANCE, HKEY, HANDLE

    class ShellExecuteInfoW(ctypes.Structure):
        _fields_ = [
            ('cbSize', DWORD),
            ('fMask', ULONG),
            ('hwnd', HWND),
            ('lpVerb', LPCWSTR),
            ('lpFile', LPCWSTR),
            ('lpParameters', LPCWSTR),
            ('lpDirectory', LPCWSTR),
            ('nShow', INT),
            ('hInstApp', HINSTANCE),
            ('lpIDList', ctypes.c_void_p),
            ('lpClass', LPCWSTR),
            ('hkeyClass', HKEY),
            ('dwHotKey', DWORD),
            ('hIcon', HANDLE),
            ('hProcess', HANDLE)]

    sei = ShellExecuteInfoW()
    sei.fMask = 0x00000040 | 0x00008000  # SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE
    sei.lpVerb = kwargs.get('verb', u'runas')  # change the verb when running the tests
    sei.lpFile = u'cmd.exe'
    sei.lpParameters = params
    sei.lpDirectory = u'{}'.format(cwd) if cwd else None
    sei.nShow = int(show)
    sei.cbSize = ctypes.sizeof(sei)
    if not ctypes.windll.Shell32.ShellExecuteExW(ctypes.byref(sei)):
        raise ctypes.WinError()

    if not blocking:
        return sei.hProcess

    kernel32 = ctypes.windll.kernel32
    timeout = kwargs.get('timeout', -1)  # INFINITE = -1
    milliseconds = int(timeout * 1e3) if timeout > 0 else timeout

    ret = kernel32.WaitForSingleObject(sei.hProcess, milliseconds)
    if ret == 0:  # WAIT_OBJECT_0
        stdout = b''
        if stdout_file and os.path.isfile(stdout_file):
            with open(stdout_file, mode='rb') as fp:
                stdout = fp.read()
            os.remove(stdout_file)

        code = DWORD()
        if not kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code)):
            raise ctypes.WinError()

        if code.value != 0:
            msg = ctypes.FormatError(code.value)
            out_str = stdout.decode('utf-8', 'ignore').rstrip()
            if show:
                msg += '\nSet show=False to capture the stdout stream.'
            else:
                if not capture_stderr:
                    msg += '\nSet capture_stderr=True to see if ' \
                           'more information is available.'
                if out_str:
                    msg += '\n{}'.format(out_str)
            raise ctypes.WinError(code=code.value, descr=msg)

        kernel32.CloseHandle(sei.hProcess)
        return stdout

    if ret == 0xFFFFFFFF:  # WAIT_FAILED
        raise ctypes.WinError()

    if ret == 0x00000080:  # WAIT_ABANDONED
        msg = 'The specified object is a mutex object that was not ' \
              'released by the thread that owned the mutex object before ' \
              'the owning thread terminated. Ownership of the mutex ' \
              'object is granted to the calling thread and the mutex state ' \
              'is set to non-signaled. If the mutex was protecting persistent ' \
              'state information, you should check it for consistency.'
    elif ret == 0x00000102:  # WAIT_TIMEOUT
        msg = "The timeout interval elapsed after {} second(s) and the " \
              "object's state is non-signaled.".format(timeout)
    else:
        msg = 'Unknown return value 0x{:x}'.format(ret)

    raise WindowsError('WaitForSingleObject: ' + msg)
