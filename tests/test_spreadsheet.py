from __future__ import annotations

import string

import pytest

from msl.io.readers.spreadsheet import Spreadsheet, to_ranges


def test_to_indices() -> None:  # noqa: C901
    to_indices = Spreadsheet.to_indices

    assert to_indices("A0") == (0, 0)
    assert to_indices("A1") == (0, 0)
    assert to_indices("AA2") == (1, 26)
    assert to_indices("AAA123") == (122, 702)
    assert to_indices("XFD123456789") == (123456788, 16383)

    for c in ["", "1", "A:B", "A1C10", "1A1"]:
        with pytest.raises(ValueError, match=r"Invalid cell"):
            _ = to_indices(c)
    for c in string.punctuation:
        with pytest.raises(ValueError, match=r"Invalid cell"):
            _ = to_indices("A" + c)
        with pytest.raises(ValueError, match=r"Invalid cell"):
            _ = to_indices(c + "A")
        with pytest.raises(ValueError, match=r"Invalid cell"):
            _ = to_indices("A1" + c)
        with pytest.raises(ValueError, match=r"Invalid cell"):
            _ = to_indices(c + "A1")

    index = 0
    uppercase = string.ascii_uppercase

    # single letter
    for c in uppercase:
        assert to_indices(c) == (None, index)
        index += 1

    # two letters
    for i in range(26):
        first = uppercase[i]
        for c in uppercase:
            assert to_indices(first + c) == (None, index)
            index += 1

    # three letters
    for i in range(26):
        first = uppercase[i]
        for j in range(26):
            second = uppercase[j]
            for c in uppercase:
                assert to_indices(first + second + c) == (None, index)
                index += 1

    # four letters
    for i in range(26):
        first = uppercase[i]
        for j in range(26):
            second = uppercase[j]
            for k in range(26):
                third = uppercase[k]
                for c in uppercase:
                    assert to_indices(first + second + third + c) == (None, index)
                    index += 1


def test_to_letters() -> None:  # noqa: C901
    to_letters = Spreadsheet.to_letters

    # negative
    for index in [-1, -10, -100, -1000]:
        assert to_letters(index) == ""

    index = 0
    uppercase = string.ascii_uppercase

    # single letter
    for c in uppercase:
        assert to_letters(index) == c
        index += 1

    # two letters
    for i in range(26):
        first = uppercase[i]
        for c in uppercase:
            assert to_letters(index) == first + c
            index += 1

    # three letters
    for i in range(26):
        first = uppercase[i]
        for j in range(26):
            second = uppercase[j]
            for c in uppercase:
                assert to_letters(index) == first + second + c
                index += 1

    # four letters
    for i in range(26):
        first = uppercase[i]
        for j in range(26):
            second = uppercase[j]
            for k in range(26):
                third = uppercase[k]
                for c in uppercase:
                    assert to_letters(index) == first + second + third + c
                    index += 1


def test_to_letters_to_indices() -> None:
    to_indices = Spreadsheet.to_indices
    to_letters = Spreadsheet.to_letters
    for index in range(1, int(1e5)):
        assert to_indices(to_letters(index) + str(index)) == (index - 1, index)


@pytest.mark.parametrize(
    ("cells", "expected"),
    [
        ("A1", (False, 0, 1, [0])),
        ("Z10", (False, 9, 10, [25])),
        ("AC4", (False, 3, 4, [28])),
        ("D", (True, 0, None, [3])),
        ("B,AA", (True, 0, None, [1, 26])),
        ("C,R5:T10", (True, 4, 10, [2, 17, 18, 19])),
        ("C:E,H", (True, 0, None, [2, 3, 4, 7])),
        ("Z,C:E", (True, 0, None, [25, 2, 3, 4])),
        ("R:T10,Z,AB:AD", (True, 0, 10, [17, 18, 19, 25, 27, 28, 29])),
        ("A1:B1", (True, 0, 1, [0, 1])),
        ("B2:G4", (True, 1, 4, [1, 2, 3, 4, 5, 6])),
        ("A1:A1", (True, 0, 1, [0])),
    ],
)
def test_to_ranges(cells: str, expected: tuple[bool, int, int | None, list[int]]) -> None:
    assert to_ranges(cells) == expected
