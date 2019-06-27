import os
import tempfile

import numpy as np

from msl.io import JSONWriter, read, HDF5Writer
from msl.io.readers.json_ import JSONReader

from helper import read_sample


def test_sample():
    root1 = read_sample('json_sample.json')

    # write as JSON then read
    writer = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp.json')
    writer.write(root=root1, mode='w')
    root2 = read(writer.url)
    assert root2.url == writer.url
    os.remove(writer.url)

    # convert to HDF5 then back to JSON
    hdf5_writer = HDF5Writer(tempfile.gettempdir() + '/msl-hdf5-writer-temp.json')
    hdf5_writer.write(root=root1, mode='w')
    root_hdf5 = read(hdf5_writer.url)
    os.remove(hdf5_writer.url)
    writer2 = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp.h5')
    writer2.write(root=root_hdf5, mode='w')
    root3 = read(writer2.url)
    assert root3.url == writer2.url
    os.remove(writer2.url)

    for root in [root1, root2, root3]:
        assert isinstance(root, JSONReader)

        assert len(list(root.groups())) == 4
        assert len(list(root.a.groups())) == 2
        assert len(list(root.a.b.groups())) == 1
        assert len(list(root.a.b.c.groups())) == 0

        assert len(list(root.datasets())) == 2
        assert len(list(root.a.datasets())) == 1
        assert len(list(root.a.b.datasets())) == 1
        assert len(list(root.a.b.c.datasets())) == 0

        assert len(root.metadata) == 4
        assert root.metadata.foo == 'bar'
        assert root.metadata.x == 9999
        assert root.metadata['22'] == 22
        assert root.metadata['33'] == 33

        assert 'conditions' in root
        assert 'my_data' in root
        assert 'a' in root
        assert '/a/b' in root
        assert '/a/b/c' in root
        assert '/a/b/dataset2' in root

        assert root.is_group(root.conditions)
        assert root['conditions'].metadata['temperature'] == 20.0
        assert root.conditions.metadata.humidity == 45

        assert root['my_data'].metadata.meta == 999
        assert root.is_dataset(root['my_data'])
        assert 'dtype' not in root['my_data'].metadata
        assert isinstance(root['my_data'].data, np.ndarray)
        assert root['my_data'].shape == (4, 5)
        assert root['my_data'].dtype.str == '<i4'
        assert np.array_equal(root['my_data'], np.arange(20).reshape(4, 5))

        assert len(root.a.metadata) == 0

        b = root.a.b
        assert len(b.metadata) == 1
        assert b.metadata.apple == 'orange'

        c = root.a.b.c
        assert root.is_group(c)
        assert len(c.metadata) == 0

        dset = root.a.b.dataset2
        assert root.is_dataset(dset)
        assert len(dset.metadata) == 0
        assert dset.shape == (2,)
        assert dset.dtype.names == ('a', 'b', 'c', 'd', 'e')
        assert dset['a'].dtype == np.object
        assert dset['b'].dtype == np.object
        assert dset['c'].dtype == np.float
        assert dset['d'].dtype == np.float
        assert dset['e'].dtype == np.int
        assert np.array_equal(dset['a'], ['100', '100s'])
        assert np.array_equal(dset['b'], ['100s', '50+50s'])
        assert np.array_equal(dset['c'], [0.000640283, -0.000192765])
        assert np.array_equal(dset['d'], [0.0, 11.071])
        assert np.array_equal(dset['e'], [8, 9])
