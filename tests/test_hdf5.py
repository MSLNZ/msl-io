import os

from msl.io.readers.hdf5 import HDF5

from helper import read_sample


def test_hdf5():
    root = read_sample('hdf5_sample.h5')
    assert root.reader_class is HDF5

    for key, value in root.items():
        print(key, value)

    order = ['D0', 'G0', 'G1A', 'D1', 'G1B', 'D2', 'D3', 'G2']
    for i, key in enumerate(root.keys()):
        assert os.path.basename(key) == order[i]

    assert len(root.metadata) == 3
    assert root.metadata['version_h5py'] == '2.8.0'
    assert root.metadata.version_hdf5 == '1.10.2'
    assert root.metadata['date_created'] == '2018-08-28 15:16:43.904990'

    assert 'D0' in root
    assert 'G0' in root

    d0 = root['D0']
    assert root.is_dataset(d0)
    assert d0.data.shape == (10, 4)
    assert d0.data.dtype.str == '<f4'
    assert len(d0.metadata) == 2
    assert d0.metadata['temperature'] == 21.2
    assert d0.metadata.temperature_units == 'deg C'

    g0 = root.G0
    assert root.is_group(g0)
    assert len(g0.metadata) == 1
    assert all(g0.metadata['count'] == [1, 2, 3, 4, 5])
    assert 'G1A' in g0
    assert 'G1B' in g0

    g1a = g0['G1A']
    assert root.is_group(g1a)
    assert len(g1a.metadata) == 2
    assert g1a.metadata['one'] == 1
    assert g1a.metadata['a'] == 'A'

    g1b = g0['G1B']
    assert root.is_group(g1b)
    assert len(g1b.metadata) == 2
    assert g1b.metadata['one'] == 1
    assert g1b.metadata['b'] == 'B'

    assert 'D1' in g0['G1A']
    d1 = root.G0.G1A.D1
    assert root.is_dataset(d1)
    assert len(d1.metadata) == 0
    assert d1.data.shape == (3, 3)
    assert d1.data.dtype.str == '<f8'

    assert 'D2' in g1b
    assert 'D3' in g0.G1B
    assert 'G2' in root.G0.G1B

    d2 = g1b['D2']
    assert root.is_dataset(d2)
    assert len(d2.metadata) == 2
    assert d2.metadata['voltage'] == 132.4
    assert d2.metadata['voltage_units'] == 'uV'
    assert d2.data.shape == (10,)
    assert d2.data.dtype.str == '<i4'
    assert d2.data[3] == 90

    d3 = g1b.D3
    assert root.is_dataset(d3)
    assert len(d3.metadata) == 0
    assert d3.data.shape == (10,)
    assert d3.data.dtype.str == '<i4'
    assert d3.data[7] == 51

    g2 = root.G0.G1B.G2
    assert root.is_group(g2)
    assert len(g2.metadata) == 1
    assert g2.metadata['hello'] == 'world'