import os

import numpy as np
import pytest

try:
    import h5py
except ImportError:
    h5py = None

from tests.helper import metadata_equal
from tests.helper import roots_equal
from msl.io import HDF5Writer
from msl.io import JSONWriter
from msl.io import copy
from msl.io import is_dir_accessible
from msl.io import read
from msl.io import read_table

# the Z: drive (if it exists) is a mapped drive to the "Photometry & Radiometry" folder
folder = r"Z:\transfer"

skipif_not_mapped = pytest.mark.skipif(
    not is_dir_accessible(folder),
    reason="mapped drive not available"
)


@skipif_not_mapped
@pytest.mark.skipif(h5py is None, reason="h5py is not installed")
def test_hdf5():
    root = read(os.path.join(os.path.dirname(__file__), "samples", "hdf5_sample.h5"))
    w = HDF5Writer(os.path.join(folder, "msl-io-testing.h5"))
    w.write(root=root, mode="w")
    assert roots_equal(root, read(w.file))
    os.remove(w.file)


@skipif_not_mapped
def test_json():
    root = read(os.path.join(os.path.dirname(__file__), "samples", "json_sample.json"))
    w = JSONWriter(os.path.join(folder, "msl-io-testing.json"))
    w.write(root=root, mode="w")
    assert roots_equal(root, read(w.file))
    os.remove(w.file)


@skipif_not_mapped
def test_copy_and_table():
    tables = {
        "table.csv": ("msl-io-testing.csv", {}),
        "table.txt": ("msl-io-testing.txt", {}),
        "table.xls": ("msl-io-testing.xls", {"sheet": "A1"}),
    }
    for original, (file, kwargs) in tables.items():
        source = os.path.join(os.path.dirname(__file__), "samples", original)
        d1 = read_table(source, dtype=object, **kwargs)
        destination1 = os.path.join(folder)
        destination2 = os.path.join(folder, file)
        destination3 = os.path.join(folder, "msl-io-testing", "subfolder", file)
        for i, dest in enumerate([destination1, destination2, destination3]):
            dest = copy(source, dest, overwrite=True)
            d2 = read_table(dest, dtype=object, **kwargs)
            if i == 0:
                assert d1.name == d2.name
            assert np.array_equal(d1.data, d2.data)
            assert metadata_equal(d1.metadata, d2.metadata)
            os.remove(dest)
        sub_folder = os.path.dirname(destination3)
        os.rmdir(sub_folder)
        os.rmdir(os.path.dirname(sub_folder))
