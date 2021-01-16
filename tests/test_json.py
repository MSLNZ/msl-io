# -*- coding: utf-8 -*-
import os
import tempfile

import numpy as np
import pytest
try:
    import h5py
except ImportError:
    h5py = None

from msl.io import JSONWriter, read, HDF5Writer
from msl.io.readers import JSONReader

from helper import read_sample


def test_sample():
    root1 = read_sample('json_sample.json')

    # write as JSON then read
    writer = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp.json')
    writer.write(root=root1, mode='w')
    root2 = read(writer.file)
    assert root2.file == writer.file
    os.remove(writer.file)

    # convert to HDF5 then back to JSON
    hdf5_writer = HDF5Writer(tempfile.gettempdir() + '/msl-hdf5-writer-temp.h5')
    # HDF5 does not support "null". So, reload the JSON file and pop the metadata
    # that contain "null" before writing the HDF5 file
    temp = read_sample('json_sample.json')
    temp.is_read_only = False
    assert temp.metadata.pop('null') is None
    assert 'null' not in temp.metadata
    array_mixed_null = temp.metadata.pop('array_mixed_null')
    assert isinstance(array_mixed_null, np.ndarray)
    assert np.array_equal(array_mixed_null, ['a', False, 5, 72.3, 'hey', None])
    assert 'array_mixed_null' not in temp.metadata
    if h5py is not None:
        hdf5_writer.write(root=temp, mode='w')
        root_hdf5 = read(hdf5_writer.file)
        os.remove(hdf5_writer.file)
        writer2 = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp2.json')
        writer2.write(root=root_hdf5, mode='w')
        root3 = read(writer2.file)
        assert root3.file == writer2.file
        os.remove(writer2.file)

    roots = [root1, root2]
    if h5py is not None:
        roots.append(root3)

    for root in roots:
        assert isinstance(root, JSONReader)

        assert len(list(root.groups())) == 4
        assert len(list(root.a.groups())) == 2
        assert len(list(root.a.b.groups())) == 1
        assert len(list(root.a.b.c.groups())) == 0

        assert len(list(root.datasets())) == 2
        assert len(list(root.a.datasets())) == 1
        assert len(list(root.a.b.datasets())) == 1
        assert len(list(root.a.b.c.datasets())) == 0

        # HDF5 does not support NULL type values
        # also, "array_mixed" gets converted to be all strings by h5py
        if h5py is not None and root is root3:
            assert len(root.metadata) == 9
            # use tolist() not np.array_equal
            assert root.metadata.array_mixed.tolist() == ['True', '-5', '0.002345', 'something', '49.1871524']
        else:
            assert len(root.metadata) == 11
            assert root.metadata.null is None
            # use tolist() not np.array_equal
            assert root.metadata.array_mixed_null.tolist() == ['a', False, 5, 72.3, 'hey', None]
            assert root.metadata.array_mixed.tolist() == [True, -5, 0.002345, 'something', 49.1871524]

        assert root.metadata.foo == 'bar'
        assert root.metadata.boolean is True
        assert root.metadata['integer'] == -99
        assert root.metadata['float'] == 33.33e3
        assert root.metadata['empty_list'].size == 0
        # use tolist() not np.array_equal
        assert root.metadata.array_strings.tolist() == ['aaa', 'bbb', 'ccc', 'ddd', 'eee']
        assert root.metadata.array_var_strings.tolist() == ['a', 'ab', 'abc', 'abcd', 'abcde']
        assert root.metadata.array_numbers.tolist() == [1, 2.3, 4, -4e99]

        # make sure the Metadata values are read only
        with pytest.raises(ValueError):
            root.metadata['new_key'] = 'new value'
        with pytest.raises(ValueError):
            del root.metadata.foo
        with pytest.raises(ValueError):
            root.metadata.boolean = False
        with pytest.raises(ValueError):
            root.metadata.array_strings[0] = 'new string'
        with pytest.raises(ValueError):
            del root.metadata.array_var_strings
        with pytest.raises(ValueError):
            root.metadata.array_numbers[:] = [-9, -8, -7, -6]

        root.is_read_only = False

        # can now modify the Metadata
        del root.metadata.foo
        assert 'foo' not in root.metadata
        root.metadata.boolean = False
        assert root.metadata.boolean is False
        root.metadata.array_strings[0] = 'new string'
        # use tolist() not np.array_equal
        assert root.metadata.array_strings.tolist() == ['new string', 'bbb', 'ccc', 'ddd', 'eee']
        root.metadata.array_numbers[::2] = [-9, -8.8]
        assert root.metadata.array_numbers.tolist() == [-9, 2.3, -8.8, -4e99]
        assert 'new_key' not in root.metadata
        root.metadata.new_key = 'new value'
        assert root.metadata.new_key == 'new value'

        root.is_read_only = True

        # make sure the Metadata values are read only again
        with pytest.raises(ValueError):
            del root.metadata.new_key
        with pytest.raises(ValueError):
            root.metadata.boolean = True
        with pytest.raises(ValueError):
            root.metadata.array_strings[-1] = 'another string'
        with pytest.raises(ValueError):
            del root.metadata.array_var_strings
        with pytest.raises(ValueError):
            root.metadata.array_numbers[:] = [11, 22, 33, 44]

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
        assert len(b.metadata) == 2
        assert b.metadata.apple == 'orange'
        assert b.metadata.pear == 'banana'

        c = root.a.b.c
        assert root.is_group(c)
        assert len(c.metadata) == 0

        dset = root.a.b.dataset2
        assert root.is_dataset(dset)
        assert len(dset.metadata) == 1
        # use tolist() not np.array_equal
        assert dset.metadata.fibonacci.tolist() == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        assert dset.shape == (2,)
        assert dset.dtype.names == ('a', 'b', 'c', 'd', 'e')
        assert dset['a'].dtype == np.object
        assert dset['b'].dtype == np.object
        assert dset['c'].dtype == np.float
        assert dset['d'].dtype == np.float
        assert dset['e'].dtype == np.int32
        assert dset['a'].tolist() == ['100', '100s']
        assert dset['b'].tolist() == ['100s', '50+50s']
        assert dset['c'].tolist() == [0.000640283, -0.000192765]
        assert dset['d'].tolist() == [0.0, 11.071]
        assert dset['e'].tolist() == [8, 9]

        # make sure the ndarray's are read only
        with pytest.raises(ValueError):
            dset.metadata.fibonacci[4] = -9
        with pytest.raises(ValueError):
            dset['e'] = [-1, 0]

        root.is_read_only = False

        dset.metadata.fibonacci[4] = -9
        assert dset.metadata.fibonacci.tolist() == [1, 1, 2, 3, -9, 8, 13, 21, 34, 55]
        dset['e'] = [-1, 0]
        assert dset['e'].tolist() == [-1, 0]

        root.is_read_only = True

        # make sure the ndarray's are read only again
        with pytest.raises(ValueError):
            dset.metadata.fibonacci[4] = 0
        with pytest.raises(ValueError):
            dset['a'][0] = 'foo'


def test_url_and_root():
    root = read_sample('json_sample.json')

    writer = JSONWriter()

    # no file was specified
    with pytest.raises(ValueError) as e:
        writer.write(root=root)
    assert 'must specify a file' in str(e.value)

    # cannot overwrite a file by default
    file = tempfile.gettempdir() + '/msl-json-writer-temp.json'
    with open(file, 'wt') as fp:
        fp.write('Hi')
    with pytest.raises(IOError) as e:
        writer.write(file=file, root=root)
    assert 'exists' in str(e.value)

    # by specifying the mode one can overwrite a file
    writer.write(file=file, root=root, mode='w')
    os.remove(file)

    # root must be a Root
    with pytest.raises(TypeError) as e:
        writer.write(file='whatever', root=list(root.datasets())[0])
    assert 'Root' in str(e.value)
    with pytest.raises(TypeError) as e:
        writer.write(file='whatever', root=list(root.groups())[0])
    assert 'Root' in str(e.value)
    with pytest.raises(TypeError) as e:
        writer.write(file='whatever', root='Root')
    assert 'Root' in str(e.value)


def test_pretty_printing():
    root = read_sample('json_sample.json')
    root.is_read_only = False

    root.create_dataset('aaa', data=np.ones((3, 3, 3)))

    w = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp.json')
    w.save(root=root, mode='w', sort_keys=True, separators=(', ', ': '))

    expected = """#File created with: MSL JSONWriter version 1.0
{
  "a": {
    "b": {
      "apple": "orange",
      "c": {},
      "dataset2": {
        "data": [
          ["100", "100s", 0.000640283, 0.0, 8],
          ["100s", "50+50s", -0.000192765, 11.071, 9]
        ],
        "dtype": [
          ["a", "object"],
          ["b", "object"],
          ["c", "float64"],
          ["d", "float64"],
          ["e", "int32"]
        ],
        "fibonacci": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
      },
      "pear": "banana"
    }
  },
  "aaa": {
    "data": [
      [
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
      ],
      [
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
      ],
      [
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
      ]
    ],
    "dtype": "<f8"
  },
  "array_mixed": [true, -5, 0.002345, "something", 49.1871524],
  "array_mixed_null": ["a", false, 5, 72.3, "hey", null],
  "array_numbers": [1, 2.3, 4, -4e+99],
  "array_strings": ["aaa", "bbb", "ccc", "ddd", "eee"],
  "array_var_strings": ["a", "ab", "abc", "abcd", "abcde"],
  "boolean": true,
  "conditions": {
    "humidity": 45,
    "temperature": 20.0
  },
  "empty_list": [],
  "float": 33330.0,
  "foo": "bar",
  "integer": -99,
  "my_data": {
    "data": [
      [0, 1, 2, 3, 4],
      [5, 6, 7, 8, 9],
      [10, 11, 12, 13, 14],
      [15, 16, 17, 18, 19]
    ],
    "dtype": "<i4",
    "meta": 999
  },
  "null": null
}
""".splitlines()

    with open(w.file, 'rt') as fp:
        written = [line.rstrip() for line in fp.read().splitlines()]

    assert len(expected) == len(written)
    for i in range(len(expected)):
        assert expected[i] == written[i]

    # make sure that we can still read the file
    root = read_sample(w.file)

    # change the indentation to be 0
    w.save(root=root, mode='w', sort_keys=True, indent=0, separators=(', ', ': '))
    with open(w.file, 'rt') as fp:
        written = [line.rstrip() for line in fp.read().splitlines()]
    assert len(expected) == len(written)
    for i in range(len(expected)):
        assert expected[i].lstrip() == written[i]

    # change the indentation to be None
    w.save(root=root, mode='w', sort_keys=True, indent=None, separators=(',', ':'))
    with open(w.file, 'rt') as fp:
        written = fp.read().splitlines()
    assert len(written) == 2
    assert written[0] == '#File created with: MSL JSONWriter version 1.0'
    assert written[1].startswith('{"a":{"b":{"apple":')
    assert written[1].endswith('},"null":null}')

    os.remove(w.file)


def test_unicode():
    def do_asserts(r):
        assert len(r.metadata) == 2
        assert u'μ' in r.metadata
        assert u'\u03bc' in r.metadata
        assert 'unit' in r.metadata
        assert r.metadata[u'μ'] == 'micro'
        assert r.metadata[u'\u03bc'] == 'micro'
        assert r.metadata.unit == u'°C'
        assert r.metadata.unit == u'\xb0C'

    root = read_sample(u'uñicödé.json')
    do_asserts(root)

    for b in [False, True]:
        writer = JSONWriter(tempfile.gettempdir() + '/msl-json-writer-temp.json')
        writer.save(root=root, ensure_ascii=b, mode='w')

        root2 = read(writer.file)
        do_asserts(root2)

        os.remove(writer.file)
