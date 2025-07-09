"""General functions."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, overload

from .google_api import GMail

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from subprocess import Popen
    from typing import Any, AnyStr, Literal

    from .types import FileLikeRead, PathLike, ReadLike, SupportsRead, WriteLike


logger = logging.getLogger(__package__)


def checksum(
    file: PathLike | FileLikeRead[bytes], *, algorithm: str = "sha256", chunk_size: int = 65536, shake_length: int = 256
) -> str:
    """Get the checksum of a file.

    A checksum is a sequence of numbers and letters that act as a fingerprint
    for a file against which later comparisons can be made to detect errors or
    changes in the file. It can be used to verify the integrity of the file.

    Args:
        file: A file to get the checksum of.
        algorithm: The hash algorithm to use to compute the checksum. See [hashlib][] for more details.
        chunk_size: The number of bytes to read at a time from the file. It is useful
            to tweak this parameter when reading a large file to improve performance.
        shake_length: The digest length to use for the `shake_128` or `shake_256` algorithm.
            See [hexdigest][hashlib.shake.hexdigest] for more details.

    Returns:
        The checksum value (which only contains hexadecimal digits).
    """
    import hashlib  # noqa: PLC0415

    def _read(fp: FileLikeRead[bytes]) -> None:
        # read in chucks to avoid loading the entire file at once
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            _hash.update(data)

    _hash = hashlib.new(algorithm)

    if isinstance(file, (str, bytes, os.PathLike)):
        with Path(os.fsdecode(file)).open("rb") as f:
            _read(f)
    else:
        position = file.tell()
        _read(file)
        _ = file.seek(position)

    try:
        return _hash.hexdigest()
    except TypeError:
        return _hash.hexdigest(shake_length)  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue,reportUnknownVariableType]


def copy(
    source: PathLike,
    destination: PathLike,
    *,
    overwrite: bool = False,
    include_metadata: bool = True,
    follow_symlinks: bool = True,
) -> Path:
    """Copy a file.

    Args:
        source: The path to a file to copy.
        destination: A directory to copy the file to or a full path (i.e., includes the basename).
            If the directory does not exist then it, and all intermediate directories, will be created.
        overwrite: Whether to overwrite the `destination` file if it already exists. If `destination`
            already exists and `overwrite` is `False` then a [FileExistsError][] is raised.
        include_metadata: Whether to also copy information such as the file permissions,
            the latest access time and latest modification time with the file.
        follow_symlinks: Whether to follow symbolic links.
            !!! note "Added in version 0.2"

    Returns:
        The path to where the file was copied.
    """
    import shutil  # noqa: PLC0415

    src = Path(os.fsdecode(source))
    dst = Path(os.fsdecode(destination))
    if dst.is_dir():
        dst = dst / src.name
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite and dst.is_file():
        msg = f"Will not overwrite {destination!r}"
        raise FileExistsError(msg)

    _ = shutil.copyfile(src, dst, follow_symlinks=follow_symlinks)
    if include_metadata:
        shutil.copystat(src, dst, follow_symlinks=follow_symlinks)

    return dst


def is_admin() -> bool:
    """Check if the current process is being run as an administrator.

    Returns:
        `True` if the current process is being run as an administrator, otherwise `False`.
    """
    import ctypes  # noqa: PLC0415

    try:
        is_admin: int = ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        if sys.platform != "win32":
            return os.geteuid() == 0
        return False
    else:
        return is_admin == 1


def is_dir_accessible(path: PathLike, *, strict: bool = False) -> bool:
    """Check if a directory exists and is accessible.

    An accessible directory is one that the user has permission to access.

    Args:
        path: The directory to check.
        strict: Whether to raise an exception if the directory is not accessible.

    Returns:
        Whether the directory exists and is accessible.
    """
    cwd = Path.cwd()
    try:
        os.chdir(path)
    except (OSError, TypeError):
        if strict:
            raise
        return False
    else:
        os.chdir(cwd)
        return True


def is_file_readable(file: PathLike, *, strict: bool = False) -> bool:
    """Check if a file exists and is readable.

    Args:
        file: The file to check.
        strict: Whether to raise an exception if the file does not exist or is not readable.

    Returns:
        Whether the file exists and is readable.
    """
    try:
        with Path(os.fsdecode(file)).open("rb"):
            return True
    except (OSError, TypeError):
        if strict:
            raise
        return False


def search(  # noqa: C901, PLR0913
    directory: PathLike,
    *,
    depth: int | None = 0,
    include: str | re.Pattern[str] | None = None,
    exclude: str | re.Pattern[str] | None = None,
    flags: int = 0,
    ignore_os_error: bool = True,
    ignore_hidden_folders: bool = True,
    follow_symlinks: bool = True,
) -> Generator[Path]:
    r"""Search for files starting from a root directory.

    Args:
        directory: The root directory to begin searching for files.
        depth: The number of sub-directories to recursively search for files.
            If `0`, only files in `directory` are searched, if `1` then files in `directory`
            and in one sub-directory are searched, etc. If `None`, search `directory` and
            recursively search all sub-directories.
        include: A regular-expression pattern to use to include files. If `None`, no filtering
            is applied and all files are yielded (that are not `exclude`d). For example,

            * `r"data"` &#8594; find files with the word `data` in the file path
            * `r"\.png$"` &#8594; find files with the extension `.png`
            * `r"\.jpe*g$"` &#8594; find files with the extension `.jpeg` or `.jpg`

        exclude: A regular-expression pattern to use to exclude files. The `exclude` pattern
            has precedence over the `include` pattern. For example,

            * `r"bin"` &#8594; exclude all files that contain the word `bin` in the file path
            * `r"bin|lib"` &#8594; exclude all files that contain the word `bin` or `lib` in the file path

        flags: The flags to use to compile regular-expression pattern (if it is a [str][] type).
        ignore_os_error: Whether to ignore an [OSError][], if one occurs, while iterating through a directory.
            This type of error can occur if a directory does not have the appropriate read permission.
        ignore_hidden_folders: Whether to ignore a hidden directory from the search. A hidden directory
            starts with a `.` (a dot).
        follow_symlinks: Whether to search for files by following symbolic links.

    Yields:
        The path to a file.
    """
    if depth is not None and depth < 0:
        return

    folder = Path(os.fsdecode(directory))

    if ignore_hidden_folders and folder.name.startswith("."):
        logger.debug("search ignored hidden folder '%s'", folder)
        return

    if isinstance(exclude, str):
        exclude = re.compile(exclude, flags=flags)

    if isinstance(include, str):
        include = re.compile(include, flags=flags)

    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file():
                    path = entry.path
                    if exclude and exclude.search(path):
                        logger.debug("search excluded file %r", path)
                    elif include is None or include.search(path):
                        yield Path(path)
                elif entry.is_dir(follow_symlinks=follow_symlinks):
                    yield from search(
                        entry,
                        depth=None if depth is None else depth - 1,
                        include=include,
                        exclude=exclude,
                        flags=flags,
                        ignore_os_error=ignore_os_error,
                        ignore_hidden_folders=ignore_hidden_folders,
                        follow_symlinks=follow_symlinks,
                    )
    except OSError:
        logger.debug("search raised OSError for '%s'", folder)
        if not ignore_os_error:
            raise


@dataclass
class _SMTPConfig:
    frm: str
    to: list[str]
    host: str
    port: int
    starttls: bool | None
    username: str | None
    password: str | None


@dataclass
class _GMailConfig:
    frm: str
    to: list[str]
    account: str | None
    credentials: str | None
    scopes: list[str] | None


def send_email(
    config: PathLike | SupportsRead[AnyStr],
    recipients: str | list[str],
    sender: str | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> None:
    """Send an email.

    Args:
        config: An INI-style configuration file that contains information on how to send
            an email. There are two ways to send an email &mdash; Gmail API or SMTP server.

            An example INI file to use the Gmail API is the following (see
            [GMmail][msl.io.google_api.GMail] for more details). Although all
            key-value pairs are optional, a `[gmail]` section must exist to use
            the Gmail API. If a key is omitted, the value passed to
            [GMmail][msl.io.google_api.GMail] is `None`

            ```ini
            [gmail]
            account = work
            credentials = path/to/client_secrets.json
            scopes =
                https://www.googleapis.com/auth/gmail.send
                https://www.googleapis.com/auth/gmail.metadata
            domain = @gmail.com
            ```

            An example INI file for an SMTP server is the following. Only the `host`
            and `port` key-value pairs are required.

            ```ini
            [smtp]
            host = hostname or IP address of the SMTP server
            port = port number to connect to on the SMTP server (e.g., 25)
            starttls = true|yes|1|on -or- false|no|0|off (default: false)
            username = the username to authenticate with (default: None)
            password = the password for username (default: None)
            domain = @company.com (default: None)
            ```

            !!! warning
                Since this information is specified in plain text in the configuration
                file, you should set the file permissions provided by your operating
                system to ensure that your authentication credentials are safe.

        recipients: The email address(es) of the recipient(s). Can omit the `@domain.com`
            part if a `domain` key is specified in the `config` file. Can use the value
            `'me'` if sending an email to yourself via Gmail.
        sender: The email address of the sender. Can omit the `@domain.com` part
            if a `domain` key is specified in the `config` file. If `sender` is not
            specified, it becomes the value of the first `recipient` if using SMTP
            or the value `'me'` if using Gmail.
        subject: The text to include in the subject field.
        body: The text to include in the body of the email. The text can be enclosed
            in `<html></html>` tags to use HTML elements to format the message.
    """
    cfg = _prepare_email(config, recipients, sender)
    if isinstance(cfg, _SMTPConfig):
        from email.mime.multipart import MIMEMultipart  # noqa: PLC0415
        from email.mime.text import MIMEText  # noqa: PLC0415
        from smtplib import SMTP  # noqa: PLC0415

        with SMTP(host=cfg.host, port=cfg.port) as server:
            if cfg.starttls:
                _ = server.ehlo()
                _ = server.starttls()
                _ = server.ehlo()
            if cfg.username and cfg.password:
                _ = server.login(cfg.username, cfg.password)
            msg = MIMEMultipart()
            msg["From"] = cfg.frm
            msg["To"] = ", ".join(cfg.to)
            msg["Subject"] = subject or "(no subject)"
            text = body or ""
            subtype = "html" if text.startswith("<html>") else "plain"
            msg.attach(MIMEText(text, subtype))
            _ = server.sendmail(cfg.frm, cfg.to, msg.as_string())
    else:
        with GMail(account=cfg.account, credentials=cfg.credentials, scopes=cfg.scopes) as gmail:
            gmail.send(cfg.to, sender=cfg.frm, subject=subject, body=body)


def _prepare_email(  # noqa: C901, PLR0912
    config: PathLike | SupportsRead[AnyStr], recipients: str | list[str], sender: str | None
) -> _GMailConfig | _SMTPConfig:
    """Loads a configuration file to prepare for sending an email."""
    from configparser import ConfigParser  # noqa: PLC0415

    contents = Path(os.fsdecode(config)).read_text() if isinstance(config, (str, bytes, os.PathLike)) else config.read()
    if isinstance(contents, bytes):
        contents = contents.decode()

    cp = ConfigParser()
    cp.read_string(contents)

    has_smtp = cp.has_section("smtp")
    has_gmail = cp.has_section("gmail")
    if has_smtp and has_gmail:
        msg = "Cannot specify both a 'gmail' and 'smtp' section"
        raise ValueError(msg)
    if not (has_smtp or has_gmail):
        msg = "Must create either a 'gmail' or 'smtp' section"
        raise ValueError(msg)

    section = cp["gmail"] if has_gmail else cp["smtp"]

    domain = section.get("domain")
    if domain and not domain.startswith("@"):
        domain = "@" + domain

    if isinstance(recipients, str):
        recipients = [recipients]

    for i in range(len(recipients)):
        if domain and "@" not in recipients[i] and (has_smtp or (has_gmail and recipients[i] != "me")):
            recipients[i] += domain

    if not sender:
        sender = "me" if has_gmail else recipients[0]
    elif domain and ("@" not in sender) and (has_smtp or (has_gmail and sender != "me")):
        sender += domain

    if has_smtp:
        host, port = section.get("host"), section.getint("port")
        if not (host and port):
            msg = "Must specify the 'host' and 'port' of the SMTP server"
            raise ValueError(msg)

        username, password = section.get("username"), section.get("password")
        if username and not password:
            msg = "Must specify the 'password' since a 'username' is specified"
            raise ValueError(msg)
        if password and not username:
            msg = "Must specify the 'username' since a 'password' is specified"
            raise ValueError(msg)

        return _SMTPConfig(
            to=recipients,
            frm=sender,
            host=host,
            port=port,
            starttls=section.getboolean("starttls"),
            username=username,
            password=password,
        )

    scopes = section.get("scopes")
    return _GMailConfig(
        to=recipients,
        frm=sender,
        account=section.get("account"),
        credentials=section.get("credentials"),
        scopes=scopes.split() if scopes else None,
    )


def get_basename(obj: PathLike | ReadLike | WriteLike) -> str:
    """Get the basename (the final path component) of a file.

    Args:
        obj: The object to get the basename of. If `obj` is an in-memory file-like
            object then the class [__name__][definition.__name__] of `obj` is returned.

    Returns:
        The basename of `obj`.
    """
    if isinstance(obj, (str, bytes, os.PathLike)):
        return Path(os.fsdecode(obj)).name

    try:
        return Path(obj.name).name
    except AttributeError:
        return obj.__class__.__name__


@dataclass(frozen=True)
class GitHead:
    """Information about the [HEAD]{:target="_blank"} of a git repository.

    This class is returned from the [git_head][msl.io.utils.git_head] function.

    [HEAD]: https://git-scm.com/docs/gitglossary#def_HEAD
    """

    hash: str
    timestamp: datetime

    @overload
    def __getitem__(self, item: Literal["hash"]) -> str: ...

    @overload
    def __getitem__(self, item: Literal["timestamp"]) -> datetime: ...

    def __getitem__(self, item: str) -> str | datetime:
        """git_head() used to return a dict, treat the dataclass like a read-only dict."""
        value: str | datetime = getattr(self, item)
        return value


def git_head(directory: PathLike) -> GitHead | None:
    """Get information about the [HEAD]{:target="_blank"} of a repository.

    This function requires that [git](https://git-scm.com/){:target="_blank"} is installed and
    that it is available on the `PATH` environment variable.

    [HEAD]: https://git-scm.com/docs/gitglossary#def_HEAD

    Args:
        directory: A directory that is under version control.

    Returns:
        Information about the most recent commit on the current branch.
            If `directory` is not a directory that is under version control
            then returns `None`.
    """
    cmd = ["git", "show", "-s", "--format=%H %ct", "HEAD"]
    try:
        out = subprocess.check_output(cmd, cwd=directory, stderr=subprocess.PIPE)  # noqa: S603
    except subprocess.CalledProcessError:
        return None

    sha, timestamp = out.split()
    return GitHead(hash=sha.decode("ascii"), timestamp=datetime.fromtimestamp(int(timestamp)))  # noqa: DTZ006


def remove_write_permissions(path: PathLike) -> None:
    """Remove all write permissions of a file.

    On Windows, this function will set the file attribute to be read only.

    On Linux and macOS, write permission is removed for the User,
    Group and Others. The read and execute permissions are preserved.

    Args:
        path: The path to remove the write permissions of.
    """
    import stat  # noqa: PLC0415

    current_permissions = stat.S_IMODE(os.lstat(path).st_mode)
    disable_writing = ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
    os.chmod(path, current_permissions & disable_writing)  # noqa: PTH101


def run_as_admin(  # noqa: C901, PLR0912, PLR0913, PLR0915
    args: PathLike | Sequence[PathLike] | None = None,
    *,
    executable: PathLike | None = None,
    cwd: PathLike | None = None,
    capture_stderr: bool = False,
    blocking: bool = True,
    show: bool = False,
    **kwargs: Any,
) -> int | bytes | Popen[Any]:
    """Run a process as an administrator and return its output.

    Args:
        args: A sequence of program arguments or else a command string. Providing a sequence of
            arguments is generally preferred, as it allows the subprocess to take care of any required
            escaping and quoting of arguments (e.g., to permit spaces in file names).
        executable: The executable to pass the `args` to.
        cwd: The working directory to use for the elevated process.
        capture_stderr: Whether to send the stderr stream to stdout.
        blocking: Whether to wait for the process to finish before returning to the calling program.
        show: Whether to show the elevated console (Windows only). If `True`, the stdout stream of
            the process is not captured.
        kwargs: If the current process already has admin privileges or if the operating system is
            not Windows then all additional keyword arguments are passed to [subprocess.check_output][].
            Otherwise, only a `timeout` keyword argument is used (Windows).

    Returns:
        The returned object depends on whether the process is executed in blocking or non-blocking mode
        and whether Python is already running with admin privileges.
        If blocking, [bytes][] are returned (the stdout stream of the process). If non-blocking, the
        returned object will either be the [subprocess.Popen][] instance that is running the
        process (POSIX) or an [int][] which is the process ID (Windows).
    """
    if not args and not executable:
        msg = "Must specify the args and/or an executable"
        raise ValueError(msg)

    stderr = subprocess.STDOUT if capture_stderr else None
    process = subprocess.check_output if blocking else subprocess.Popen

    if is_admin():
        if not args:
            assert executable is not None  # noqa: S101
            return process(executable, cwd=cwd, stderr=stderr, **kwargs)  # pyright: ignore[reportUnknownVariableType]
        return process(args, executable=executable, cwd=cwd, stderr=stderr, **kwargs)  # pyright: ignore[reportUnknownVariableType]

    exe = "" if executable is None else subprocess.list2cmdline([os.fsdecode(executable)])

    if os.name != "nt":
        if not args:
            command = ["sudo", exe]
        elif isinstance(args, (str, bytes, os.PathLike)):
            command = ["sudo", exe, os.fsdecode(args)]
        else:
            command = ["sudo", exe, *list(map(os.fsdecode, args))]
        return process(command, cwd=cwd, stderr=stderr, **kwargs)  # pyright: ignore[reportUnknownVariableType]

    # Windows is more complicated

    if args is None:
        args = ""
    elif isinstance(args, (bytes, os.PathLike)):
        args = os.fsdecode(args)

    if not isinstance(args, str):
        args = subprocess.list2cmdline(args)

    cwd = os.getcwd() if not cwd else os.fsdecode(cwd)  # noqa: PTH109

    # the 'runas' verb starts in C:\WINDOWS\system32
    cd = subprocess.list2cmdline(["cd", "/d", cwd, "&&"])

    # check if a Python environment needs to be activated
    activate = ""
    if exe == sys.executable or args.startswith(sys.executable):
        conda = os.getenv("CONDA_PREFIX")  # conda
        venv = os.getenv("VIRTUAL_ENV")  # venv
        if conda:
            env = os.getenv("CONDA_DEFAULT_ENV")
            if not env:
                msg = "CONDA_DEFAULT_ENV environment variable does not exist"
                raise ValueError(msg)
            if env == "base":
                bat = Path(conda) / "Scripts" / "activate.bat"
            else:
                bat = Path(conda).parent.parent / "Scripts" / "activate.bat"
            if not bat.is_file():
                msg = f"Cannot find {bat}"
                raise FileNotFoundError(msg)
            activate = subprocess.list2cmdline([bat, env, "&&"])
        elif venv:
            bat = Path(venv) / "Scripts" / "activate.bat"
            if not bat.is_file():
                msg = f"Cannot find {bat}"
                raise FileNotFoundError(msg)
            activate = subprocess.list2cmdline([bat, "&&"])

    # redirect stdout (stderr) to a file
    redirect = None
    stdout_file = None
    if not show:
        import tempfile  # noqa: PLC0415
        import uuid  # noqa: PLC0415

        stdout_file = Path(tempfile.gettempdir()) / str(uuid.uuid4())
        r = [">", str(stdout_file)]
        if capture_stderr:
            r.append("2>&1")
        redirect = subprocess.list2cmdline(r)
        if re.search(r"\d$", args):
            # this number is also considered as a file handle, so add a space
            redirect = " " + redirect

    # the string that is passed to cmd.exe
    params = f'/S /C "{cd} {activate} {exe} {args}"{redirect}'

    import ctypes  # noqa: PLC0415
    from ctypes.wintypes import DWORD, HANDLE, HINSTANCE, HKEY, HWND, INT, LPCWSTR, ULONG  # noqa: PLC0415

    class ShellExecuteInfoW(ctypes.Structure):
        _fields_ = (  # pyright: ignore[reportUnannotatedClassAttribute]
            ("cbSize", DWORD),
            ("fMask", ULONG),
            ("hwnd", HWND),
            ("lpVerb", LPCWSTR),
            ("lpFile", LPCWSTR),
            ("lpParameters", LPCWSTR),
            ("lpDirectory", LPCWSTR),
            ("nShow", INT),
            ("hInstApp", HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", LPCWSTR),
            ("hkeyClass", HKEY),
            ("dwHotKey", DWORD),
            ("hIcon", HANDLE),
            ("hProcess", HANDLE),
        )

    sei = ShellExecuteInfoW()
    sei.fMask = 0x00000040 | 0x00008000  # SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE
    sei.lpVerb = kwargs.get("verb", "runas")  # change the verb when running the tests
    sei.lpFile = "cmd.exe"
    sei.lpParameters = params
    sei.lpDirectory = f"{cwd}" if cwd else None
    sei.nShow = int(show)
    sei.cbSize = ctypes.sizeof(sei)
    if not ctypes.windll.Shell32.ShellExecuteExW(ctypes.byref(sei)):
        raise ctypes.WinError()

    if not blocking:
        return cast("int", sei.hProcess)

    kernel32 = ctypes.windll.kernel32
    timeout = kwargs.get("timeout", -1)  # INFINITE = -1
    milliseconds = int(timeout * 1e3) if timeout > 0 else timeout

    ret = kernel32.WaitForSingleObject(sei.hProcess, milliseconds)
    if ret == 0:  # WAIT_OBJECT_0
        stdout = b""
        if stdout_file is not None and stdout_file.is_file():
            stdout = stdout_file.read_bytes()
            stdout_file.unlink()

        code = DWORD()
        if not kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code)):
            raise ctypes.WinError()

        if code.value != 0:
            msg = ctypes.FormatError(code.value)
            out_str = stdout.decode("utf-8", "ignore").rstrip()
            if show:
                msg += "\nSet show=False to capture the stdout stream."
            else:
                if not capture_stderr:
                    msg += "\nSet capture_stderr=True to see if more information is available."
                if out_str:
                    msg += f"\n{out_str}"
            raise ctypes.WinError(code.value, msg)

        kernel32.CloseHandle(sei.hProcess)
        return stdout

    if ret == 0xFFFFFFFF:  # WAIT_FAILED  # noqa: PLR2004
        raise ctypes.WinError()

    if ret == 0x00000080:  # WAIT_ABANDONED  # noqa: PLR2004
        msg = (
            "The specified object is a mutex object that was not "
            "released by the thread that owned the mutex object before "
            "the owning thread terminated. Ownership of the mutex "
            "object is granted to the calling thread and the mutex state "
            "is set to non-signalled. If the mutex was protecting persistent "
            "state information, you should check it for consistency."
        )
    elif ret == 0x00000102:  # WAIT_TIMEOUT  # noqa: PLR2004
        msg = f"The timeout interval elapsed after {timeout} second(s) and the object's state is non-signalled."
    else:
        msg = f"Unknown return value 0x{ret:x}"

    msg = f"WaitForSingleObject: {msg}"
    raise OSError(msg)
