import string

import pytest

from msl.io.readers.spreadsheet import Spreadsheet


def test_to_indices() -> None:  # noqa: C901
    to_indices = Spreadsheet.to_indices

    assert to_indices("A0") == (0, 0)
    assert to_indices("A1") == (0, 0)
    assert to_indices("AA2") == (1, 26)
    assert to_indices("AAA123") == (122, 702)
    assert to_indices("XFD123456789") == (123456788, 16383)

    for c in ["", "1", "A:B", "A1C10", "1A1"]:
        with pytest.raises(ValueError, match="Invalid cell"):
            _ = to_indices(c)
    for c in string.punctuation:
        with pytest.raises(ValueError, match="Invalid cell"):
            _ = to_indices("A" + c)
        with pytest.raises(ValueError, match="Invalid cell"):
            _ = to_indices(c + "A")
        with pytest.raises(ValueError, match="Invalid cell"):
            _ = to_indices("A1" + c)
        with pytest.raises(ValueError, match="Invalid cell"):
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


def test_to_slices() -> None:
    to_slices = Spreadsheet.to_slices
    for cells in ["", "A", "A:B:", ":"]:
        with pytest.raises(ValueError, match="Invalid cell"):
            _ = to_slices(cells)
    assert to_slices("A:A") == (slice(0, None, None), slice(0, 1, None))
    assert to_slices("A:G") == (slice(0, None, None), slice(0, 7, None))
    assert to_slices("A1:A100") == (slice(0, 100, None), slice(0, 1, None))
    assert to_slices("A2:G10", row_step=2, column_step=2) == (slice(1, 10, 2), slice(0, 7, 2))
    assert to_slices("H25:AA47", column_step=2) == (slice(24, 47, None), slice(7, 27, 2))
    assert to_slices("HF11:JK4321", row_step=5) == (slice(10, 4321, 5), slice(213, 271, None))
