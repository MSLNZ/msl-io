"""Configuration file for doctests."""

# cSpell: ignore doctests
from __future__ import annotations

import os
from importlib.util import find_spec
from typing import TYPE_CHECKING

import pytest
from google.auth.exceptions import GoogleAuthError

from msl.io.google_api import GSheets

if TYPE_CHECKING:
    from typing import Callable


os.environ["MSL_IO_RUNNING_TESTS"] = "True"


try:
    _ = GSheets(account="testing", read_only=True)
except (OSError, GoogleAuthError):
    has_read_token = False
else:
    has_read_token = True


def check_h5py() -> None:
    """Skip doctest if h5py is not installed.

    h5py 2.10.0 was the last release to provide wheels for Windows x86 on PyPI (Python <= 3.8).
    """
    if find_spec("h5py") is None:
        pytest.skip("h5py not installed")


def skip_admin() -> None:
    """Skip run-as-admin doctest."""
    pytest.skip("illustrative examples")


def check_sheets_read_token() -> None:
    """Skip doctest if the GSheet API token is not available."""
    if not has_read_token:
        pytest.skip("GSheet API token not available")


@pytest.fixture(autouse=True)
def doctest_skipif(doctest_namespace: dict[str, Callable[[], None]]) -> None:
    """Inject skipif conditions for doctest."""
    doctest_namespace.update(
        {
            "SKIP_IF_NO_H5PY": check_h5py,
            "SKIP_IF_NO_GOOGLE_SHEETS_READ_TOKEN": check_sheets_read_token,
            "SKIP_RUN_AS_ADMIN": skip_admin,
        }
    )
