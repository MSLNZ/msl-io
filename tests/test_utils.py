from __future__ import annotations

import datetime
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from io import BufferedReader, BytesIO, StringIO, TextIOWrapper
from pathlib import Path

import pytest

from msl.io import utils
from msl.io.utils import _GMailConfig, _prepare_email, _SMTPConfig  # pyright: ignore[reportPrivateUsage]


def test_search() -> None:
    # the msl-io folder
    d = Path(__file__).parent.parent
    assert d.name.endswith("msl-io")

    # (?!c) means match __init__.py files but ignore __init__.pyc files
    files = list(utils.search(d, include=r"__init__\.py(?!c)"))
    assert len(files) == 0

    files = list(utils.search(d, include=r"__init__\.py$", depth=3))
    assert len(files) == 1
    for file in files:
        assert file.name == "__init__.py"

    files = list(utils.search(d, include=r"__init__\.py$", depth=None, exclude=r"v?env"))
    assert len(files) == 4
    for file in files:
        assert file.name == "__init__.py"

    files = list(utils.search(d, include=r"__init__\.py(?!c)", depth=None, exclude=r"readers|v?env"))
    assert len(files) == 2
    for file in files:
        assert file.name == "__init__.py"

    files = list(utils.search(d, include=r"__init__\.py$", depth=None, exclude=r"readers|writers|v?env"))
    assert len(files) == 1
    for file in files:
        assert file.name == "__init__.py"

    files = list(utils.search(d, include=r"license"))
    assert len(files) == 0

    files = list(utils.search(d, include=r"license", flags=re.IGNORECASE))
    assert len(files) == 1
    for file in files:
        assert file.name == "LICENSE.txt"

    files = list(utils.search(d, include=re.compile(r"license", flags=re.IGNORECASE)))
    assert len(files) == 1
    for file in files:
        assert file.name == "LICENSE.txt"

    files = list(utils.search(d, depth=1, include=r"git", ignore_hidden_folders=True))
    assert len(files) == 1
    for file in files:
        assert file.name == ".gitignore"

    files = list(utils.search(d, depth=1, include=r"git", exclude=r"ignore", ignore_hidden_folders=True))
    assert len(files) == 0

    files = list(utils.search(d, depth=1, include=r"git", ignore_hidden_folders=False))
    assert len(files) > 1

    files = list(utils.search(d, include=r"\.(toml|json)$"))
    assert len(files) == 2

    files = list(utils.search("does-not-exist"))
    assert len(files) == 0

    with pytest.raises(FileNotFoundError, match=r"does-not-exist"):
        _ = list(utils.search("does-not-exist", ignore_os_error=False))


def test_git_head() -> None:
    root_dir = Path(__file__).parent.parent

    head = utils.git_head(root_dir)
    assert head is not None
    assert len(head.hash) == 40
    assert all(char.isalnum() for char in head.hash)
    assert all(char.isalnum() for char in head["hash"])
    assert isinstance(head.hash, str)
    assert isinstance(head.timestamp, datetime.datetime)
    assert head.timestamp.year > 2024
    assert head["timestamp"].year > 2024

    head = utils.git_head(str(root_dir))
    assert head is not None

    head = utils.git_head(str(root_dir).encode())
    assert head is not None

    # can specify any directory within the version control hierarchy
    assert utils.git_head(root_dir / ".git") == head
    assert utils.git_head(root_dir / "src" / "msl" / "io" / "readers") == head

    # a directory not under version control
    assert utils.git_head(tempfile.gettempdir()) is None


def test_checksum() -> None:
    path = Path(__file__).parent / "samples" / "hdf5_sample.h5"
    sha256 = "e5dad4f15335e603fd602c22bf9ddb71b3500f862905495d3d17e6159a463d2d"
    md5 = "a46708df266595218db2ba06788c4695"

    # use a filename as Path
    assert sha256 == utils.checksum(path, algorithm="sha256")
    assert md5 == utils.checksum(path, algorithm="md5")

    # use a filename as a string
    assert sha256 == utils.checksum(str(path), algorithm="sha256")
    assert md5 == utils.checksum(str(path), algorithm="md5")

    # use a filename as bytes
    assert sha256 == utils.checksum(str(path).encode(), algorithm="sha256")
    assert md5 == utils.checksum(str(path).encode(), algorithm="md5")

    # use a file pointer (binary mode)
    with path.open("rb") as fp:
        assert sha256 == utils.checksum(fp, algorithm="sha256")
    with path.open("rb") as fp:
        assert md5 == utils.checksum(fp, algorithm="md5")

    # use a byte buffer
    with path.open("rb") as fp:
        buffer = BytesIO(fp.read())
    assert buffer.tell() == 0
    assert sha256 == utils.checksum(buffer, algorithm="sha256")
    assert buffer.tell() == 0
    assert md5 == utils.checksum(buffer, algorithm="md5")
    assert buffer.tell() == 0

    # ensure that all available algorithms can be used
    for algorithm in hashlib.algorithms_available:
        if sys.version_info[:2] == (3, 8):
            if sys.platform.startswith("linux") and algorithm in ("ripemd160", "whirlpool", "md4"):
                continue
            if sys.platform == "darwin" and algorithm in ("md4", "mdc2", "whirlpool"):
                continue
        value = utils.checksum(path, algorithm=algorithm)
        assert isinstance(value, str)

    # file does not exist
    with pytest.raises(OSError, match="does_not_exist.txt"):
        _ = utils.checksum("/the/file/does_not_exist.txt")
    with pytest.raises(OSError, match="does_not_exist.txt"):
        _ = utils.checksum(b"/the/file/does_not_exist.txt")

    # invalid file type
    with pytest.raises(AttributeError):
        _ = utils.checksum(None)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
    with pytest.raises(AttributeError):
        _ = utils.checksum(bytearray(b"data"))  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
    with pytest.raises(AttributeError):
        _ = utils.checksum(memoryview(b"data"))  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    # unsupported algorithm
    with pytest.raises(ValueError, match=r"unsupported"):
        _ = utils.checksum(path, algorithm="invalid")


def test_get_basename() -> None:
    paths = [
        "/a/b/c/d/e/file.dat",
        "file.dat",
        "/a/file.dat",
        "/something/file.dat",
        "file://a.b.c.d/folder/file.dat",
    ]
    if sys.platform == "win32":
        paths.extend(
            [
                "C:\\a\\b\\c\\d\\e\\file.dat",
                r"C:\a\file.dat",
                "D:/file.dat",
                r"\\a.b.c.d\folder\file.dat",
                "\\\\a.b.c.d\\folder\\file.dat",
            ]
        )
    for path in paths:
        assert utils.get_basename(path) == "file.dat"
        assert utils.get_basename(path.encode()) == "file.dat"
        assert utils.get_basename(Path(path)) == "file.dat"

    assert utils.get_basename(StringIO("hello")) == "StringIO"
    assert utils.get_basename(BytesIO(b"hello")) == "BytesIO"

    with Path(__file__).open("rb") as fp:
        assert utils.get_basename(fp) == "test_utils.py"

    with Path(__file__).open() as fp:
        assert utils.get_basename(fp) == "test_utils.py"


def test_copy() -> None:  # noqa: C901, PLR0915
    def check_stat(dest: Path) -> bool:  # noqa: C901
        src_stat = Path(__file__).stat()
        dst_stat = dest.stat()
        for attr in dir(src_stat):
            if not attr.startswith("st_"):
                continue
            if attr in ["st_ino", "st_ctime", "st_ctime_ns", "st_birthtime", "st_birthtime_ns"]:  # these won't equal
                continue
            src_value = getattr(src_stat, attr)
            dst_value = getattr(dst_stat, attr)
            if attr == "st_file_attributes":
                # on Windows the FILE_ATTRIBUTE_NOT_CONTENT_INDEXED attribute may not be copied
                if (src_value != dst_value) and (src_value + 0x2000 != dst_value):
                    return False
            elif "time" in attr:  # times can be approximate
                if attr.endswith("ns"):
                    if abs(src_value - dst_value) > 1e4:
                        return False
                elif abs(src_value - dst_value) > 1e-4:
                    return False
            elif attr == "st_dev" and sys.platform == "win32" and os.getenv("GITHUB_ACTIONS"):
                # the ST_DEV values are not equal if the tests are run
                # via GitHub Actions and the OS is Windows
                pass
            elif src_value != dst_value:
                return False
        return True

    # make sure there is no remnant file from a previously-failed test
    (Path(tempfile.gettempdir()) / "test_utils.py").unlink(missing_ok=True)

    # source file does not exist
    for item in [r"/the/file/does_not_exist.txt", r"/the/file/does_not_exist", r"does_not_exist"]:
        with pytest.raises(OSError, match="does_not_exist"):
            _ = utils.copy(item, "")

    # copy (with metadata) to a directory that already exists
    dst = utils.copy(__file__, tempfile.gettempdir())
    assert dst == Path(tempfile.gettempdir()) / "test_utils.py"
    assert check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)

    # destination already exists
    with pytest.raises(OSError, match=r"Will not overwrite"):
        _ = utils.copy(__file__, dst)
    with pytest.raises(OSError, match=r"Will not overwrite"):
        _ = utils.copy(__file__, tempfile.gettempdir())

    # can overwrite (with metadata), specify full path
    dst2 = utils.copy(__file__, dst, overwrite=True)
    assert dst2 == dst
    assert check_stat(dst2)
    assert utils.checksum(__file__) == utils.checksum(dst2)

    # can overwrite (without metadata), specify full path
    dst3 = utils.copy(__file__, dst, overwrite=True, include_metadata=False)
    assert dst3 == dst
    assert not check_stat(dst3)
    assert utils.checksum(__file__) == utils.checksum(dst3)

    # can overwrite (with metadata), specify directory only
    dst4 = utils.copy(__file__, tempfile.gettempdir(), overwrite=True)
    assert dst4 == dst
    assert check_stat(dst4)
    assert utils.checksum(__file__) == utils.checksum(dst4)

    dst.unlink()

    # copy without metadata
    dst = utils.copy(__file__, tempfile.gettempdir(), include_metadata=False)
    assert dst == Path(tempfile.gettempdir()) / "test_utils.py"
    assert not check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    dst.unlink()

    # copy (without metadata) but use a different destination basename
    destination = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.tmp"
    dst = utils.copy(__file__, destination, include_metadata=False)
    assert dst == destination
    assert not check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    dst.unlink()

    # copy to a directory that does not exist
    new_dirs = str(uuid.uuid4()).split("-")
    assert not (Path(tempfile.gettempdir()) / new_dirs[0]).is_dir()
    destination = Path(tempfile.gettempdir()).joinpath(*new_dirs)
    destination = destination / "new_file.tmp"
    dst = utils.copy(__file__, destination)
    assert dst == destination
    assert check_stat(dst)
    assert utils.checksum(__file__) == utils.checksum(dst)
    shutil.rmtree(Path(tempfile.gettempdir()) / new_dirs[0])


def test_remove_write_permissions() -> None:
    # create a new file
    path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.tmp"
    _ = path.write_bytes(b"hello")

    # set to rwxrwxrwx  # cSpell: ignore rwxrwxrwx
    path.chmod(0o777)

    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == "win32":  # Windows does not have the Execute permission
        assert mode == 0o666
    else:
        assert mode == 0o777

    # can still modify it
    with path.open("ab") as fp:
        _ = fp.write(b" world")
    with path.open("rb") as fp:
        assert fp.read() == b"hello world"

    utils.remove_write_permissions(path)

    # the Read and Execute permissions are preserved
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == "win32":  # Windows does not have the Execute permission
        assert mode == 0o444
    else:
        assert mode == 0o555

    # cannot open the file to modify it
    for m in ["wb", "ab", "wt", "at", "w+", "w+b"]:
        with pytest.raises(OSError, match="denied"):
            _ = path.open(m)

    # cannot delete the file (only valid on Windows)
    if sys.platform == "win32":
        with pytest.raises(OSError, match="denied"):
            path.unlink()

    # can still read it
    with path.open("rb") as fp:
        assert fp.read() == b"hello world"

    # set to rw--wxrw-  # cSpell: ignore wxrw
    path.chmod(0o636)

    # remove and check permissions
    utils.remove_write_permissions(path)
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if sys.platform == "win32":
        # Windows does not have the Execute permission
        # and if any of the Read permissions are enabled then it
        # is enabled for the User, Group and Others
        assert mode == 0o444
    else:
        assert mode == 0o414

    # clean up by deleting the file
    path.chmod(0o777)
    path.unlink()


def test_is_file_readable() -> None:
    assert utils.is_file_readable(__file__)
    assert utils.is_file_readable(__file__.encode())
    assert utils.is_file_readable(Path(__file__))

    # Not a valid file path
    assert not utils.is_file_readable("")
    assert not utils.is_file_readable(__file__ + "py")

    # Not a PathLike object
    assert not utils.is_file_readable(None)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
    assert not utils.is_file_readable({})  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError):
        _ = utils.is_file_readable(None, strict=True)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    with pytest.raises(OSError, match=r"does-not-exist.txt"):
        _ = utils.is_file_readable("does-not-exist.txt", strict=True)


def test_is_dir_accessible() -> None:
    path = Path(__file__).parent
    assert utils.is_dir_accessible(path)
    assert utils.is_dir_accessible(str(path))
    assert utils.is_dir_accessible(str(path).encode())

    # Not a valid directory path
    assert not utils.is_dir_accessible("")
    assert not utils.is_dir_accessible(__file__)

    # Not a PathLike object
    assert not utils.is_dir_accessible(None)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
    assert not utils.is_dir_accessible({})  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError):
        _ = utils.is_dir_accessible(None, strict=True)  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    with pytest.raises(OSError, match=r"test_utils\.py"):
        _ = utils.is_dir_accessible(__file__, strict=True)


def test_is_admin() -> None:
    assert utils.is_admin() in {True, False}


@pytest.mark.skipif(utils.is_admin(), reason="don't run if already an admin")
@pytest.mark.skipif(os.name != "nt", reason="non-Windows OS")
def test_run_as_admin() -> None:  # noqa: PLR0915
    # Using verb=None as a keyword argument allows for testing the
    # 'run_as_admin' function without getting the UAC prompt,
    # but the test command must not require admin privileges.
    # Only test on a non-admin Windows session because the other cases:
    #   1) already an admin
    #   2) running on POSIX
    # are straightforward implementations and we don't want to test
    # the subprocess.check_output internals.

    with pytest.raises(ValueError, match=r"args and/or an executable$"):
        _ = utils.run_as_admin()

    # Don't want Windows to return b'ECHO is on.\r\n'
    out = utils.run_as_admin(args="echo 1", verb=None)
    assert out == b"1 \r\n"
    out = utils.run_as_admin(args=["echo", "1"], verb=None)
    assert out == b"1 \r\n"

    # no extra space after "hi"
    out = utils.run_as_admin(args="echo hi", verb=None)
    assert out == b"hi\r\n"

    # pass in the keyword argument "args=" as a positional argument
    out = utils.run_as_admin("echo hi", verb=None)
    assert out == b"hi\r\n"

    # run a batch file with spaces in the file path and in the arguments
    file = Path(tempfile.gettempdir()) / "msl io batch script.bat"
    with file.open("wt") as fp:
        _ = fp.write("@ECHO OFF\r\n")
        for i in range(1, 6):
            _ = fp.write(f"echo %{i}\r\n")

    expected = b"ECHO is off.\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\n"
    out = utils.run_as_admin(args=f'"{file}"', verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file], verb=None)
    assert out == expected
    out = utils.run_as_admin(executable=file, verb=None)
    assert out == expected

    expected = b"pi\r\n-p\r\nECHO is off.\r\nECHO is off.\r\nECHO is off.\r\n"
    out = utils.run_as_admin(args=f'"{file}" pi -p', verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, "pi", "-p"], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=["pi", "-p"], executable=file, verb=None)
    assert out == expected

    expected = b'pi\r\n-p\r\n"hel lo"\r\nECHO is off.\r\nECHO is off.\r\n'
    out = utils.run_as_admin(args=f'"{file}" pi -p "hel lo"', verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, "pi", "-p", "hel lo"], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=["pi", "-p", "hel lo"], executable=file, verb=None)
    assert out == expected

    expected = b'pi\r\n-p\r\n"hel lo"\r\n6\r\n"last parameter received"\r\n'
    out = utils.run_as_admin(args=f'"{file}" pi -p "hel lo" 6 "last parameter received"', verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, "pi", "-p", "hel lo", "6", "last parameter received"], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=["pi", "-p", "hel lo", "6", "last parameter received"], executable=file, verb=None)
    assert out == expected

    # change directory
    out = utils.run_as_admin(
        args=[file.name, "pi", "-p", "hel lo", "6", "last parameter received"], cwd=file.parent, verb=None
    )
    assert out == expected

    file.unlink()

    # call the Python interpreter
    expected = subprocess.check_output([sys.executable, "-VV"])  # noqa: S603
    out = utils.run_as_admin(args="-VV", executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=f"{sys.executable} -VV", verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, "-VV"], verb=None)
    assert out == expected
    out = utils.run_as_admin(args=["-VV"], executable=sys.executable, verb=None)
    assert out == expected

    # run a python script
    file = Path(tempfile.gettempdir()) / "msl_io_admin_test.py"
    with file.open("wt") as fp:
        _ = fp.write("import sys\r\n")
        # additional packages must be available since msl-io depends on them
        _ = fp.write("import numpy\r\n")
        _ = fp.write("print(sys.executable)\r\n")
        _ = fp.write("print(sys.argv[1:])\r\n")
        _ = fp.write('print("written to stderr", file=sys.stderr)\r\n')

    # no arguments
    expected = f"{sys.executable}\r\n[]\r\n".encode()
    out = utils.run_as_admin(args=file, executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=f"{sys.executable} {file}", verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file], executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, file], verb=None)
    assert out == expected

    # with arguments
    expected = f"{sys.executable}\r\n['1', 'x=5', 'a b c d', 'e']\r\n".encode()
    out = utils.run_as_admin(args=f'{file} 1 x=5 "a b c d" e', executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=f'{sys.executable} {file} 1 x=5 "a b c d" e', verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[file, "1", "x=5", "a b c d", "e"], executable=sys.executable, verb=None)
    assert out == expected
    out = utils.run_as_admin(args=[sys.executable, file, "1", "x=5", "a b c d", "e"], verb=None)
    assert out == expected

    # change directory
    expected = f"{sys.executable}\r\n['1']\r\n".encode()
    out = utils.run_as_admin(args=[sys.executable, file.name, "1"], cwd=file.parent, verb=None)
    assert out == expected

    # set capture_stderr=True
    out = utils.run_as_admin(args=[sys.executable, file], capture_stderr=True, verb=None)
    assert isinstance(out, bytes)
    assert b"written to stderr" in out

    file.unlink()

    # raise some exceptions
    with pytest.raises(PermissionError):
        _ = utils.run_as_admin('sc create MSL-IO-TEST binPath= "C:\\hello world\\dummy.exe"', verb=None)

    with pytest.raises(PermissionError):
        _ = utils.run_as_admin(["sc", "create", "MSL-IO-TEST", "binPath=", "C:\\hello world\\dummy.exe"], verb=None)

    with pytest.raises(OSError, match=r"Set capture_stderr=True to see if more information is available.$"):
        _ = utils.run_as_admin("doesnotexist.exe", verb=None)

    with pytest.raises(OSError, match=r"'doesnotexist.exe' is not recognized as an internal or external command"):
        _ = utils.run_as_admin("doesnotexist.exe", capture_stderr=True, verb=None)

    with pytest.raises(OSError, match=r"Set show=False to capture the stdout stream.$"):
        _ = utils.run_as_admin([sys.executable, "-c", "1/0"], show=True, verb=None)

    with pytest.raises(OSError, match=r"Set capture_stderr=True to see if more information is available.$"):
        _ = utils.run_as_admin([sys.executable, "-c", "1/0"], verb=None)

    with pytest.raises(OSError, match=r"Set capture_stderr=True to see if more information is available.\nHello!$"):
        _ = utils.run_as_admin([sys.executable, "-c", 'print("Hello!");1/0'], verb=None)

    with pytest.raises(OSError, match=r"ZeroDivisionError:"):
        _ = utils.run_as_admin([sys.executable, "-c", "1/0"], capture_stderr=True, verb=None)


def test_prepare_email() -> None:  # noqa: PLR0915
    temp = Path(tempfile.gettempdir()) / "793a7e5d-7e0e-4049-9e9b-f4383b7bb96a.tmp"

    def create(lines: list[str]) -> None:
        _ = temp.write_text("\n".join(lines))

    with pytest.raises(OSError, match="does-not-exist.ini"):
        _ = _prepare_email("does-not-exist.ini", "", "")

    create(["[smtp]", "[gmail]"])
    with pytest.raises(ValueError, match="Cannot specify both"):
        _ = _prepare_email(temp, "", None)

    create(["[unknown]"])
    with pytest.raises(ValueError, match="Must create either"):
        _ = _prepare_email(temp, "", None)

    for item in (["[smtp]"], ["[smtp]", "host=hostname"], ["[smtp]", "port=25"]):
        create(item)
        with pytest.raises(ValueError, match="Must specify the 'host' and 'port'"):
            _ = _prepare_email(temp, "", None)

    create(["[smtp]", "port=not-an-int"])
    with pytest.raises(ValueError, match="invalid literal for int()"):
        _ = _prepare_email(temp, "", None)

    create(["[smtp]", "host=smtp.example.com", "port=25"])
    cfg = _prepare_email(temp, "", None)
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == [""]
    assert cfg.frm == ""
    assert cfg.host == "smtp.example.com"
    assert cfg.port == 25
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    create(["[smtp]", "host=h", "port=1"])
    cfg = _prepare_email(temp, "name", None)
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["name"]
    assert cfg.frm == "name"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    create(["[smtp]", "host=h", "port=1", "domain=domain"])
    cfg = _prepare_email(temp, "name", None)
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["name@domain"]
    assert cfg.frm == "name@domain"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    create(["[smtp]", "host=h", "port=1", "domain=@domain"])
    cfg = _prepare_email(temp, ["name0", "name1", "name2"], None)
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["name0@domain", "name1@domain", "name2@domain"]
    assert cfg.frm == "name0@domain"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    create(["[smtp]", "host=h", "port=1", "domain=@domain"])
    cfg = _prepare_email(temp, "name@mail.com", None)
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["name@mail.com"]
    assert cfg.frm == "name@mail.com"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    create(["[smtp]", "host=h", "port=1", "domain=@domain"])
    cfg = _prepare_email(temp, ["you@mail.com", "me"], "me")
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["you@mail.com", "me@domain"]
    assert cfg.frm == "me@domain"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is None
    assert cfg.username is None
    assert cfg.password is None

    for yes in ("yes", "YES", "1", "true", "True", "on", "On"):
        create(["[smtp]", "host=h", "port=1", f"starttls={yes}"])
        cfg = _prepare_email(temp, "you", "me")
        assert isinstance(cfg, _SMTPConfig)
        assert cfg.to == ["you"]
        assert cfg.frm == "me"
        assert cfg.host == "h"
        assert cfg.port == 1
        assert cfg.starttls is True
        assert cfg.username is None
        assert cfg.password is None

    for no in ("no", "No", "0", "false", "False", "off", "Off"):
        create(["[smtp]", "host=h", "port=1", f"starttls={no}"])
        cfg = _prepare_email(temp, "you", "me")
        assert isinstance(cfg, _SMTPConfig)
        assert cfg.to == ["you"]
        assert cfg.frm == "me"
        assert cfg.host == "h"
        assert cfg.port == 1
        assert cfg.starttls is False
        assert cfg.username is None
        assert cfg.password is None

    create(["[smtp]", "host=h", "port=1", "username=user"])
    with pytest.raises(ValueError, match="Must specify the 'password'"):
        _ = _prepare_email(temp, "", None)

    create(["[smtp]", "host=h", "port=1", "password=pw"])
    with pytest.raises(ValueError, match="Must specify the 'username'"):
        _ = _prepare_email(temp, "", None)

    create(["[smtp]", "host=h", "port=1", "starttls=0", "username=uname", "password=pw"])
    cfg = _prepare_email(temp, "you", "me@mail")
    assert isinstance(cfg, _SMTPConfig)
    assert cfg.to == ["you"]
    assert cfg.frm == "me@mail"
    assert cfg.host == "h"
    assert cfg.port == 1
    assert cfg.starttls is False
    assert cfg.username == "uname"
    assert cfg.password == "pw"  # noqa: S105

    create(["[gmail]"])
    cfg = _prepare_email(temp, "", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == [""]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes is None

    cfg = _prepare_email(temp, "me", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["me"]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes is None

    create(["[gmail]", "domain=domain"])
    cfg = _prepare_email(temp, "me", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["me"]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes is None

    create(["[gmail]", "account=mine", "domain=@gmail.com"])
    cfg = _prepare_email(temp, "you", "me")
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["you@gmail.com"]
    assert cfg.frm == "me"
    assert cfg.account == "mine"
    assert cfg.credentials is None
    assert cfg.scopes is None

    create(["[gmail]", "credentials=path/to/oauth"])
    cfg = _prepare_email(temp, ["email@corp.com", "me"], None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["email@corp.com", "me"]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials == "path/to/oauth"
    assert cfg.scopes is None

    create(["[gmail]", "credentials=path\\to\\oauth", "account=work", "domain=ignored"])
    cfg = _prepare_email(temp, "name@gmail.com", "name@email.com")
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["name@gmail.com"]
    assert cfg.frm == "name@email.com"
    assert cfg.account == "work"
    assert cfg.credentials == "path\\to\\oauth"
    assert cfg.scopes is None

    create(["[gmail]", "credentials=path\\to\\oauth", "account=work", "domain=domain"])
    cfg = _prepare_email(temp, ["a", "b", "c@corp.net"], None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == ["a@domain", "b@domain", "c@corp.net"]
    assert cfg.frm == "me"
    assert cfg.account == "work"
    assert cfg.credentials == "path\\to\\oauth"
    assert cfg.scopes is None

    create(["[gmail]", "scopes=a"])
    cfg = _prepare_email(temp, "", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == [""]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes == ["a"]

    create(["[gmail]", "scopes = ", " gmail", " gmail.send", " g", " gmail.metadata", "", "", "", "account = work"])
    cfg = _prepare_email(temp, "", "")
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == [""]
    assert cfg.frm == "me"
    assert cfg.account == "work"
    assert cfg.credentials is None
    assert cfg.scopes == ["gmail", "gmail.send", "g", "gmail.metadata"]

    # file-like objects
    with temp.open("rt") as f1:
        cfg = _prepare_email(f1, "", "")
        assert isinstance(cfg, _GMailConfig)
        assert cfg.to == [""]
        assert cfg.frm == "me"
        assert cfg.account == "work"
        assert cfg.credentials is None
        assert cfg.scopes == ["gmail", "gmail.send", "g", "gmail.metadata"]

    with temp.open("rb") as f2:
        cfg = _prepare_email(f2, "", "")
        assert isinstance(cfg, _GMailConfig)
        assert cfg.to == [""]
        assert cfg.frm == "me"
        assert cfg.account == "work"
        assert cfg.credentials is None
        assert cfg.scopes == ["gmail", "gmail.send", "g", "gmail.metadata"]

    cfg = _prepare_email(StringIO("[gmail]"), "", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == [""]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes is None

    cfg = _prepare_email(BytesIO(b"[gmail]"), "", None)
    assert isinstance(cfg, _GMailConfig)
    assert cfg.to == [""]
    assert cfg.frm == "me"
    assert cfg.account is None
    assert cfg.credentials is None
    assert cfg.scopes is None

    temp.unlink()


def test_get_lines() -> None:  # noqa: PLR0915
    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_lines"

    # the file contains 26 lines
    with path.open() as fp:
        all_lines = fp.read().split("\n")

    string_io = StringIO()
    with path.open() as fp:
        data = fp.read()
        _ = string_io.write(data)
    _ = string_io.seek(0)

    open_ = path.open()

    for obj in [path, string_io, open_]:
        assert isinstance(obj, (Path, StringIO, TextIOWrapper))
        assert len(utils.get_lines(obj)) == 26
        assert len(utils.get_lines(obj, remove_empty_lines=True)) == 24

        assert utils.get_lines(obj) == all_lines
        assert utils.get_lines(obj, None) == all_lines
        assert utils.get_lines(obj, 0) == []
        assert utils.get_lines(obj, 1) == ["line1"]
        assert utils.get_lines(obj, -1) == ["line26"]
        assert utils.get_lines(obj, 5) == ["line1", "line2", "line3", "line4", "line5"]
        assert utils.get_lines(obj, -5) == ["line22", "line23", "line24", "line25", "line26"]
        assert utils.get_lines(obj, 100) == all_lines
        assert utils.get_lines(obj, -100) == all_lines

        assert utils.get_lines(obj, None, None) == all_lines
        assert utils.get_lines(obj, None, 0) == []
        assert utils.get_lines(obj, None, 1) == ["line1"]
        assert utils.get_lines(obj, None, -1) == all_lines
        assert utils.get_lines(obj, None, 5) == ["line1", "line2", "line3", "line4", "line5"]
        assert utils.get_lines(obj, None, -20) == ["line1", "line2", "line3", "line4", "line5", "line6", "line7"]
        assert utils.get_lines(obj, None, 100) == all_lines
        assert utils.get_lines(obj, None, -100) == []

        assert utils.get_lines(obj, 0, None) == all_lines
        assert utils.get_lines(obj, 1, None) == all_lines
        assert utils.get_lines(obj, -1, None) == ["line26"]
        assert utils.get_lines(obj, 18, None) == [
            "line18",
            "line19",
            "line20",
            "",
            "line22",
            "line23",
            "line24",
            "line25",
            "line26",
        ]
        assert utils.get_lines(obj, -5, None) == ["line22", "line23", "line24", "line25", "line26"]
        assert utils.get_lines(obj, 100, None) == []  # there are only 26 lines
        assert utils.get_lines(obj, -100, None) == all_lines

        assert utils.get_lines(obj, 0, 0) == []
        assert utils.get_lines(obj, 1, 1) == ["line1"]
        assert utils.get_lines(obj, 1, -1) == all_lines
        assert utils.get_lines(obj, 4, 8) == ["line4", "line5", "line6", "line7", "line8"]
        assert utils.get_lines(obj, -8, -4) == ["line19", "line20", "", "line22", "line23"]
        assert utils.get_lines(obj, 2, 4) == ["line2", "line3", "line4"]
        assert utils.get_lines(obj, -5, 4) == []
        assert utils.get_lines(obj, 10, -7) == [
            "line10",
            "",
            "line12",
            "line13",
            "line14",
            "line15",
            "line16",
            "line17",
            "line18",
            "line19",
            "line20",
        ]
        assert utils.get_lines(obj, 100, 200) == []  # there are only 26 lines
        assert utils.get_lines(obj, -100, -50) == []
        assert utils.get_lines(obj, 25, 100) == ["line25", "line26"]

        assert utils.get_lines(obj, 1, -1, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert utils.get_lines(obj, 0, None, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert utils.get_lines(obj, None, None, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert utils.get_lines(obj, 1, 15, 6) == ["line1", "line7", "line13"]
        assert utils.get_lines(obj, -20, -5, 5) == ["line7", "line12", "line17", "line22"]
        assert utils.get_lines(obj, -100, -21, 2) == ["line1", "line3", "line5"]
        assert utils.get_lines(obj, -100, -20, 2) == ["line1", "line3", "line5", "line7"]
        assert utils.get_lines(obj, 15, 25, 3) == ["line15", "line18", "", "line24"]
        assert utils.get_lines(obj, 15, 25, 3, remove_empty_lines=True) == ["line15", "line18", "line24"]

    string_io.close()
    open_.close()


def test_get_lines_bytes() -> None:
    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_lines"
    with path.open("rb") as f:
        assert utils.get_lines(f, -5) == [b"line22", b"line23", b"line24", b"line25", b"line26"]

    bytes_io = BytesIO()
    with path.open("rb") as fp:
        _ = bytes_io.write(fp.read())
    _ = bytes_io.seek(0)
    assert utils.get_lines(bytes_io, -5) == [b"line22", b"line23", b"line24", b"line25", b"line26"]


def test_get_bytes() -> None:  # noqa: PLR0915
    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_bytes"

    # the file contains 184 bytes
    with path.open("rb") as fp:
        all_bytes = fp.read()

    bytes_io = BytesIO()
    with path.open("rb") as fp:
        _ = bytes_io.write(fp.read())
    _ = bytes_io.seek(0)

    open_ = path.open("rb")

    for obj in [path, bytes_io, open_]:
        assert isinstance(obj, (Path, BytesIO, BufferedReader))
        assert utils.get_bytes(obj) == all_bytes
        assert utils.get_bytes(obj, None) == all_bytes
        assert utils.get_bytes(obj, 0) == b""
        assert utils.get_bytes(obj, 1) == b"!"
        assert utils.get_bytes(obj, -1) == b"~"
        assert utils.get_bytes(obj, 7) == b'!"#$%&('
        assert utils.get_bytes(obj, -5) == b"z{|}~"
        assert utils.get_bytes(obj, -21) == b"jklmnopqrstuvwxyz{|}~"  # cSpell: ignore jklmnopqrstuvwxyz
        assert utils.get_bytes(obj, -5000) == all_bytes
        assert utils.get_bytes(obj, 5000) == all_bytes

        assert utils.get_bytes(obj, None, None) == all_bytes
        assert utils.get_bytes(obj, None, 0) == b""
        assert utils.get_bytes(obj, None, -1) == all_bytes
        assert utils.get_bytes(obj, None, 1) == b"!"
        assert utils.get_bytes(obj, None, -179) == b'!"#$%&'  # 184 - 179 -> the first 6 bytes
        assert utils.get_bytes(obj, None, 8) == b'!"#$%&()'
        assert utils.get_bytes(obj, None, -5000) == b""
        assert utils.get_bytes(obj, None, 5000) == all_bytes

        assert utils.get_bytes(obj, 0, None) == all_bytes
        assert utils.get_bytes(obj, 1, None) == all_bytes
        assert utils.get_bytes(obj, -1, None) == b"~"
        assert utils.get_bytes(obj, 123, None) == b"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        assert utils.get_bytes(obj, -37, None) == b"YZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        assert utils.get_bytes(obj, -5000, None) == all_bytes
        assert utils.get_bytes(obj, 5000, None) == b""

        assert utils.get_bytes(obj, 0, 0) == b""
        assert utils.get_bytes(obj, 1, 1) == b"!"
        assert utils.get_bytes(obj, 1, -1) == all_bytes
        assert utils.get_bytes(obj, 5, 10) == b"%&()*+"
        assert (  # cSpell: ignore PQRSTUVWXYZ
            utils.get_bytes(obj, 139, -1) == b"PQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        )
        assert utils.get_bytes(obj, 123, -20) == b"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijk"
        assert utils.get_bytes(obj, -101, 55) == b""
        assert utils.get_bytes(obj, 33, 57) == b"BCDEFGHIJKLMNOPQRSTUVWXYZ"  # cSpell: ignore BCDEFGHIJKLMNOPQRSTUVWXYZ
        assert utils.get_bytes(obj, -10, -4) == b"uvwxyz{"  # cSpell: ignore uvwxyz
        assert utils.get_bytes(obj, 600, -600) == b""
        assert utils.get_bytes(obj, 100, 50) == b""
        assert utils.get_bytes(obj, 5000, 6000) == b""
        assert utils.get_bytes(obj, -6000, -5000) == b""

        assert utils.get_bytes(obj, 0, 6, 3) == b"!$"
        assert utils.get_bytes(obj, 1, 6, 3) == b"!$"
        assert utils.get_bytes(obj, 0, 7, 3) == b"!$("
        assert utils.get_bytes(obj, 1, 7, 3) == b"!$("
        assert utils.get_bytes(obj, 0, 8, 3) == b"!$("
        assert utils.get_bytes(obj, 1, 8, 3) == b"!$("
        assert utils.get_bytes(obj, 0, 12, 3) == b"!$(+"
        assert utils.get_bytes(obj, 1, 12, 3) == b"!$(+"
        assert utils.get_bytes(obj, 0, 13, 3) == b"!$(+."
        assert utils.get_bytes(obj, 1, 13, 3) == b"!$(+."
        assert utils.get_bytes(obj, 9, 49, 8) == b"*2:BJR"
        assert utils.get_bytes(obj, 9, 53, 8) == b"*2:BJR"
        assert utils.get_bytes(obj, -19, -5, 5) == b"lqv"
        assert utils.get_bytes(obj, -19, -4, 5) == b"lqv{"
        assert utils.get_bytes(obj, -10, -1, 2) == b"uwy{}"
        assert utils.get_bytes(obj, -11, -1, 2) == b"tvxz|~"  # cSpell: ignore tvxz
        assert utils.get_bytes(obj, -200, -155, 5) == b"!&,16;"
        assert utils.get_bytes(obj, 109, 500, 10) == b"2<FPZeoy"  # cSpell: ignore Zeoy

    bytes_io.close()
    open_.close()


def test_get_extension() -> None:
    assert utils.get_extension("") == ""
    assert utils.get_extension("xxx") == ""
    assert utils.get_extension("a.xxx") == ".xxx"
    assert utils.get_extension("/home/msl/data.csv") == ".csv"
    assert utils.get_extension("/home/msl/filename.with.dots.dat") == ".dat"
    assert utils.get_extension(StringIO()) == ""
    assert utils.get_extension(BytesIO()) == ""
    assert utils.get_extension(Path()) == ""
    assert utils.get_extension(Path("a.x")) == ".x"
    assert utils.get_extension(Path(r"C:\folder\hello.world")) == ".world"
    assert utils.get_extension(Path("filename.with.dots.dat")) == ".dat"

    path = Path(__file__).parent / "samples" / "excel_datatypes.xlsx"
    with path.open() as fp:
        assert utils.get_extension(fp) == ".xlsx"

    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_lines"
    with path.open() as fp:
        assert utils.get_extension(fp) == ""
