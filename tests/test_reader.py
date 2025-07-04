import pathlib
from io import BufferedReader, BytesIO, StringIO, TextIOWrapper
from pathlib import Path

from msl.io import Reader, Root
from msl.io.readers import JSONReader


def test_get_root() -> None:
    root = JSONReader("")
    assert isinstance(root, Root)
    assert not root.read_only


def test_instantiate() -> None:
    reader = JSONReader("aaa.bbb")
    assert reader.file == "aaa.bbb"


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
        assert len(Reader.get_lines(obj)) == 26
        assert len(Reader.get_lines(obj, remove_empty_lines=True)) == 24

        assert Reader.get_lines(obj) == all_lines
        assert Reader.get_lines(obj, None) == all_lines
        assert Reader.get_lines(obj, 0) == []
        assert Reader.get_lines(obj, 1) == ["line1"]
        assert Reader.get_lines(obj, -1) == ["line26"]
        assert Reader.get_lines(obj, 5) == ["line1", "line2", "line3", "line4", "line5"]
        assert Reader.get_lines(obj, -5) == ["line22", "line23", "line24", "line25", "line26"]
        assert Reader.get_lines(obj, 100) == all_lines
        assert Reader.get_lines(obj, -100) == all_lines

        assert Reader.get_lines(obj, None, None) == all_lines
        assert Reader.get_lines(obj, None, 0) == []
        assert Reader.get_lines(obj, None, 1) == ["line1"]
        assert Reader.get_lines(obj, None, -1) == all_lines
        assert Reader.get_lines(obj, None, 5) == ["line1", "line2", "line3", "line4", "line5"]
        assert Reader.get_lines(obj, None, -20) == ["line1", "line2", "line3", "line4", "line5", "line6", "line7"]
        assert Reader.get_lines(obj, None, 100) == all_lines
        assert Reader.get_lines(obj, None, -100) == []

        assert Reader.get_lines(obj, 0, None) == all_lines
        assert Reader.get_lines(obj, 1, None) == all_lines
        assert Reader.get_lines(obj, -1, None) == ["line26"]
        assert Reader.get_lines(obj, 18, None) == [
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
        assert Reader.get_lines(obj, -5, None) == ["line22", "line23", "line24", "line25", "line26"]
        assert Reader.get_lines(obj, 100, None) == []  # there are only 26 lines
        assert Reader.get_lines(obj, -100, None) == all_lines

        assert Reader.get_lines(obj, 0, 0) == []
        assert Reader.get_lines(obj, 1, 1) == ["line1"]
        assert Reader.get_lines(obj, 1, -1) == all_lines
        assert Reader.get_lines(obj, 4, 8) == ["line4", "line5", "line6", "line7", "line8"]
        assert Reader.get_lines(obj, -8, -4) == ["line19", "line20", "", "line22", "line23"]
        assert Reader.get_lines(obj, 2, 4) == ["line2", "line3", "line4"]
        assert Reader.get_lines(obj, -5, 4) == []
        assert Reader.get_lines(obj, 10, -7) == [
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
        assert Reader.get_lines(obj, 100, 200) == []  # there are only 26 lines
        assert Reader.get_lines(obj, -100, -50) == []
        assert Reader.get_lines(obj, 25, 100) == ["line25", "line26"]

        assert Reader.get_lines(obj, 1, -1, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert Reader.get_lines(obj, 0, None, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert Reader.get_lines(obj, None, None, 6) == ["line1", "line7", "line13", "line19", "line25"]
        assert Reader.get_lines(obj, 1, 15, 6) == ["line1", "line7", "line13"]
        assert Reader.get_lines(obj, -20, -5, 5) == ["line7", "line12", "line17", "line22"]
        assert Reader.get_lines(obj, -100, -21, 2) == ["line1", "line3", "line5"]
        assert Reader.get_lines(obj, -100, -20, 2) == ["line1", "line3", "line5", "line7"]
        assert Reader.get_lines(obj, 15, 25, 3) == ["line15", "line18", "", "line24"]
        assert Reader.get_lines(obj, 15, 25, 3, remove_empty_lines=True) == ["line15", "line18", "line24"]

    string_io.close()
    open_.close()


def test_get_lines_bytes() -> None:
    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_lines"
    with path.open("rb") as f:
        assert Reader.get_lines(f, -5) == [b"line22", b"line23", b"line24", b"line25", b"line26"]

    bytes_io = BytesIO()
    with path.open("rb") as fp:
        _ = bytes_io.write(fp.read())
    _ = bytes_io.seek(0)
    assert Reader.get_lines(bytes_io, -5) == [b"line22", b"line23", b"line24", b"line25", b"line26"]


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
        assert Reader.get_bytes(obj) == all_bytes
        assert Reader.get_bytes(obj, None) == all_bytes
        assert Reader.get_bytes(obj, 0) == b""
        assert Reader.get_bytes(obj, 1) == b"!"
        assert Reader.get_bytes(obj, -1) == b"~"
        assert Reader.get_bytes(obj, 7) == b'!"#$%&('
        assert Reader.get_bytes(obj, -5) == b"z{|}~"
        assert Reader.get_bytes(obj, -21) == b"jklmnopqrstuvwxyz{|}~"  # cSpell: ignore jklmnopqrstuvwxyz
        assert Reader.get_bytes(obj, -5000) == all_bytes
        assert Reader.get_bytes(obj, 5000) == all_bytes

        assert Reader.get_bytes(obj, None, None) == all_bytes
        assert Reader.get_bytes(obj, None, 0) == b""
        assert Reader.get_bytes(obj, None, -1) == all_bytes
        assert Reader.get_bytes(obj, None, 1) == b"!"
        assert Reader.get_bytes(obj, None, -179) == b'!"#$%&'  # 184 - 179 -> the first 6 bytes
        assert Reader.get_bytes(obj, None, 8) == b'!"#$%&()'
        assert Reader.get_bytes(obj, None, -5000) == b""
        assert Reader.get_bytes(obj, None, 5000) == all_bytes

        assert Reader.get_bytes(obj, 0, None) == all_bytes
        assert Reader.get_bytes(obj, 1, None) == all_bytes
        assert Reader.get_bytes(obj, -1, None) == b"~"
        assert Reader.get_bytes(obj, 123, None) == b"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        assert Reader.get_bytes(obj, -37, None) == b"YZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        assert Reader.get_bytes(obj, -5000, None) == all_bytes
        assert Reader.get_bytes(obj, 5000, None) == b""

        assert Reader.get_bytes(obj, 0, 0) == b""
        assert Reader.get_bytes(obj, 1, 1) == b"!"
        assert Reader.get_bytes(obj, 1, -1) == all_bytes
        assert Reader.get_bytes(obj, 5, 10) == b"%&()*+"
        assert (  # cSpell: ignore PQRSTUVWXYZ
            Reader.get_bytes(obj, 139, -1) == b"PQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        )
        assert Reader.get_bytes(obj, 123, -20) == b"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijk"
        assert Reader.get_bytes(obj, -101, 55) == b""
        assert Reader.get_bytes(obj, 33, 57) == b"BCDEFGHIJKLMNOPQRSTUVWXYZ"  # cSpell: ignore BCDEFGHIJKLMNOPQRSTUVWXYZ
        assert Reader.get_bytes(obj, -10, -4) == b"uvwxyz{"  # cSpell: ignore uvwxyz
        assert Reader.get_bytes(obj, 600, -600) == b""
        assert Reader.get_bytes(obj, 100, 50) == b""
        assert Reader.get_bytes(obj, 5000, 6000) == b""
        assert Reader.get_bytes(obj, -6000, -5000) == b""

        assert Reader.get_bytes(obj, 0, 6, 3) == b"!$"
        assert Reader.get_bytes(obj, 1, 6, 3) == b"!$"
        assert Reader.get_bytes(obj, 0, 7, 3) == b"!$("
        assert Reader.get_bytes(obj, 1, 7, 3) == b"!$("
        assert Reader.get_bytes(obj, 0, 8, 3) == b"!$("
        assert Reader.get_bytes(obj, 1, 8, 3) == b"!$("
        assert Reader.get_bytes(obj, 0, 12, 3) == b"!$(+"
        assert Reader.get_bytes(obj, 1, 12, 3) == b"!$(+"
        assert Reader.get_bytes(obj, 0, 13, 3) == b"!$(+."
        assert Reader.get_bytes(obj, 1, 13, 3) == b"!$(+."
        assert Reader.get_bytes(obj, 9, 49, 8) == b"*2:BJR"
        assert Reader.get_bytes(obj, 9, 53, 8) == b"*2:BJR"
        assert Reader.get_bytes(obj, -19, -5, 5) == b"lqv"
        assert Reader.get_bytes(obj, -19, -4, 5) == b"lqv{"
        assert Reader.get_bytes(obj, -10, -1, 2) == b"uwy{}"
        assert Reader.get_bytes(obj, -11, -1, 2) == b"tvxz|~"  # cSpell: ignore tvxz
        assert Reader.get_bytes(obj, -200, -155, 5) == b"!&,16;"
        assert Reader.get_bytes(obj, 109, 500, 10) == b"2<FPZeoy"  # cSpell: ignore Zeoy

    bytes_io.close()
    open_.close()


def test_get_extension() -> None:
    assert Reader.get_extension("") == ""
    assert Reader.get_extension("xxx") == ""
    assert Reader.get_extension("a.xxx") == ".xxx"
    assert Reader.get_extension("/home/msl/data.csv") == ".csv"
    assert Reader.get_extension("/home/msl/filename.with.dots.dat") == ".dat"
    assert Reader.get_extension(StringIO()) == ""
    assert Reader.get_extension(BytesIO()) == ""
    assert Reader.get_extension(pathlib.Path()) == ""
    assert Reader.get_extension(pathlib.Path("a.x")) == ".x"
    assert Reader.get_extension(pathlib.Path(r"C:\folder\hello.world")) == ".world"
    assert Reader.get_extension(pathlib.Path("filename.with.dots.dat")) == ".dat"

    path = Path(__file__).parent / "samples" / "excel_datatypes.xlsx"
    with path.open() as fp:
        assert Reader.get_extension(fp) == ".xlsx"

    path = Path(__file__).parent / "samples" / "test_file_for_static_Reader_lines"
    with path.open() as fp:
        assert Reader.get_extension(fp) == ""
