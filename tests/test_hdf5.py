import os
import tempfile

import numpy as np
import pytest

try:
    import h5py
except ImportError:
    h5py = None

from tests.helper import read_sample
from tests.helper import roots_equal
from msl.io import HDF5Writer
from msl.io import JSONWriter
from msl.io import read
from msl.io.readers import HDF5Reader


@pytest.mark.skipif(h5py is None, reason="h5py not installed")
def test_read_write_convert():
    root1 = read_sample("hdf5_sample.h5")

    # write as HDF5 then read
    writer = HDF5Writer(tempfile.gettempdir() + "/msl-hdf5-writer-temp.h5")
    writer.write(root=root1, mode="w")
    root2 = read(writer.file)
    assert root2.file == writer.file
    assert roots_equal(root1, root2)
    os.remove(writer.file)

    # convert to JSON then back to HDF5
    json_writer = JSONWriter(tempfile.gettempdir() + "/msl-json-writer-temp.json")
    json_writer.write(root=root1, mode="w")
    root_json = read(json_writer.file)
    assert root_json.file == json_writer.file
    assert roots_equal(root1, root_json)
    os.remove(json_writer.file)
    writer2 = HDF5Writer(tempfile.gettempdir() + "/msl-hdf5-writer-temp2.h5")
    writer2.write(root=root_json, mode="w")
    root3 = read(writer2.file)
    assert root3.file == writer2.file
    assert roots_equal(root1, root3)
    os.remove(writer2.file)

    for root in [root1, root2, root3]:
        assert isinstance(root, HDF5Reader)

        for key, value in root.items():
            k, v = str(key), str(value)
            k, v = repr(key), repr(value)

        order = ["D0", "G0", "G1A", "D1", "G1B", "D2", "D3", "G2"]
        for i, key in enumerate(root.keys()):
            assert os.path.basename(key) == order[i]

        assert len(root.metadata) == 3
        assert root.metadata["version_h5py"] == "2.8.0"
        assert root.metadata.version_hdf5 == "1.10.2"
        assert root.metadata["date_created"] == "2018-08-28 15:16:43.904990"

        assert "D0" in root
        assert "G0" in root

        d0 = root["D0"]
        assert root.is_dataset(d0)
        assert d0.shape == (10, 4)
        assert d0.dtype.str == "<f4"
        assert len(d0.metadata) == 2
        assert d0.metadata["temperature"] == 21.2
        assert d0.metadata.temperature_units == "deg C"

        g0 = root.G0
        assert root.is_group(g0)
        assert len(g0.metadata) == 1
        assert all(g0.metadata["count"] == [1, 2, 3, 4, 5])
        assert "G1A" in g0
        assert "G1B" in g0

        g1a = g0["G1A"]
        assert root.is_group(g1a)
        assert len(g1a.metadata) == 2
        assert g1a.metadata["one"] == 1
        assert g1a.metadata["a"] == "A"

        g1b = g0["G1B"]
        assert root.is_group(g1b)
        assert len(g1b.metadata) == 2
        assert g1b.metadata["one"] == 1
        assert g1b.metadata["b"] == "B"

        assert "D1" in g0["G1A"]
        d1 = root.G0.G1A.D1
        assert root.is_dataset(d1)
        assert len(d1.metadata) == 0
        assert d1.shape == (3, 3)
        assert d1.dtype.str == "<f8"

        assert "D2" in g1b
        assert "D3" in g0.G1B
        assert "G2" in root.G0.G1B

        d2 = g1b["D2"]
        assert root.is_dataset(d2)
        assert len(d2.metadata) == 2
        assert d2.metadata["voltage"] == 132.4
        assert d2.metadata["voltage_units"] == "uV"
        assert d2.shape == (10,)
        assert d2.dtype.str == "<i4"
        assert d2[3] == 90

        d3 = g1b.D3
        assert root.is_dataset(d3)
        assert len(d3.metadata) == 0
        assert d3.shape == (10,)
        assert d3.dtype.str == "<i4"
        assert d3[7] == 51

        g2 = root.G0.G1B.G2
        assert root.is_group(g2)
        assert len(g2.metadata) == 1
        assert g2.metadata["hello"] == "world"


@pytest.mark.skipif(h5py is None, reason="h5py not installed")
def test_raises():
    root = read_sample("hdf5_sample.h5")

    writer = HDF5Writer()
    assert writer.file is None

    # no file was specified
    with pytest.raises(ValueError, match=r"must specify a file"):
        writer.write(root=root)

    # root must be a Root object
    with pytest.raises(TypeError, match=r"Root"):
        writer.write(file="whatever", root=list(root.datasets())[0])
    with pytest.raises(TypeError, match=r"Root"):
        writer.write(file="whatever", root=list(root.groups())[0])
    with pytest.raises(TypeError, match=r"Root"):
        writer.write(file="whatever", root="Root")

    # cannot overwrite a file by default
    file = tempfile.gettempdir() + "/msl-hdf5-writer-temp.h5"
    with open(file, mode="wt") as fp:
        fp.write("Hi")
    with pytest.raises(OSError, match=r"File exists"):
        writer.write(file=file, root=root)
    with pytest.raises(OSError, match=r"File exists"):
        writer.write(file=file, root=root, mode="x")
    with pytest.raises(OSError, match=r"File exists"):
        writer.write(file=file, root=root, mode="w-")

    # invalid mode
    for m in ["r", "b", "w+b"]:
        with pytest.raises(ValueError, match=r"Invalid mode"):
            writer.write(file=file, root=root, mode=m)

    # r+ is a valid mode, but the file must already exist
    with pytest.raises(OSError, match=r"File does not exist"):
        writer.write(file="does_not.exist", root=root, mode="r+")

    # by specifying the proper mode one can overwrite a file
    writer.write(file=file, root=root, mode="w")
    assert roots_equal(root, read(file))
    writer.write(file=file, root=root, mode="a")
    assert roots_equal(root, read(file))
    writer.write(file=file, root=root, mode="r+")
    assert roots_equal(root, read(file))
    os.remove(file)


@pytest.mark.skipif(h5py is None, reason="h5py not installed")
def test_numpy_unicode_dtype():
    writer = HDF5Writer()
    writer.add_metadata(wide_chars=np.array(["1", "-4e+99", "True"], dtype="<U6"))
    writer.create_dataset("wide_chars", data=np.random.random(100).reshape(4, 25).astype("<U32"))

    file = tempfile.gettempdir() + "/msl-hdf5-writer-temp.h5"
    writer.save(file, mode="w")

    root = read(file)
    assert np.array_equal(root.metadata.wide_chars, writer.metadata.wide_chars)

    # the following array_equal assertion fails so we iterate over all elements instead
    # assert np.array_equal(root.wide_chars.astype('<U32'), writer.wide_chars)
    for a, b in zip(root.wide_chars.astype("<U32").flatten(), writer.wide_chars.flatten()):
        assert a == b

    os.remove(file)
