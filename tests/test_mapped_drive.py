import os
from importlib.util import find_spec
from pathlib import Path

import numpy as np
import pytest

from msl.io import HDF5Writer, JSONWriter, copy, is_dir_accessible, read, read_table

# the Z: drive (if it exists) is a mapped drive to the "Photometry & Radiometry" folder
folder = r"Z:\transfer"

skipif_not_mapped = pytest.mark.skipif(not is_dir_accessible(folder), reason="mapped drive not available")


@skipif_not_mapped
@pytest.mark.skipif(find_spec("h5py") is None, reason="h5py is not installed")
def test_hdf5() -> None:
    root = read(Path(__file__).parent / "samples" / "hdf5_sample.h5")
    w = HDF5Writer(os.path.join(folder, "msl-io-testing.h5"))  # noqa: PTH118
    w.write(root=root, mode="w")
    assert isinstance(w.file, str)
    assert root == read(w.file)
    os.remove(w.file)  # noqa: PTH107


@skipif_not_mapped
def test_json() -> None:
    root = read(Path(__file__).parent / "samples" / "json_sample.json")
    w = JSONWriter(os.path.join(folder, "msl-io-testing.json"))  # noqa: PTH118
    w.write(root=root, mode="w")
    assert isinstance(w.file, str)
    assert root == read(w.file)
    os.remove(w.file)  # noqa: PTH107


@skipif_not_mapped
def test_copy_and_table() -> None:
    tables: dict[str, tuple[str, dict[str, str]]] = {
        "table.csv": ("msl-io-testing.csv", {}),
        "table.txt": ("msl-io-testing.txt", {}),
        "table.xls": ("msl-io-testing.xls", {"sheet": "A1"}),
    }
    for original, (file, kwargs) in tables.items():
        source = Path(__file__).parent / "samples" / original
        d1 = read_table(source, dtype=object, **kwargs)
        destination1 = os.path.join(folder)  # noqa: PTH118
        destination2 = os.path.join(folder, file)  # noqa: PTH118
        destination3 = os.path.join(folder, "msl-io-testing", "subfolder", file)  # noqa: PTH118
        for i, dest in enumerate([destination1, destination2, destination3]):
            _dest = copy(source, dest, overwrite=True)
            d2 = read_table(dest, dtype=object, **kwargs)
            if i == 0:
                assert d1.name == d2.name
            assert np.array_equal(d1.data, d2.data)
            assert d1.metadata == d2.metadata
            os.remove(_dest)  # noqa: PTH107
        sub_folder = os.path.dirname(destination3)  # noqa: PTH120
        os.rmdir(sub_folder)  # noqa: PTH106
        os.rmdir(os.path.dirname(sub_folder))  # noqa: PTH106, PTH120
