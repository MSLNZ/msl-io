"""Helper functions for the tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing import Literal

    from msl.io.base import Root


def roots_equal(r1: Root, r2: Root) -> Literal[True]:
    """Assert that two Root objects are equal."""
    assert r1.metadata == r2.metadata

    groups1 = list(r1.groups())
    groups1.sort(key=lambda x: x.name)
    groups2 = list(r2.groups())
    groups2.sort(key=lambda x: x.name)
    assert len(groups1) == len(groups2)
    for g1, g2 in zip(groups1, groups2):
        assert g1.name == g2.name, f"{g1.name} != {g2.name}"
        assert g1.metadata == g2.metadata

    datasets1 = list(r1.datasets())
    datasets1.sort(key=lambda x: x.name)
    datasets2 = list(r2.datasets())
    datasets2.sort(key=lambda x: x.name)
    assert len(datasets1) == len(datasets2)
    for d1, d2 in zip(datasets1, datasets2):
        assert d1 == d2

    return True
