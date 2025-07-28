# MSL-IO

[![CI Status](https://github.com/MSLNZ/msl-io/actions/workflows/ci.yml/badge.svg)](https://github.com/MSLNZ/msl-io/actions/workflows/ci.yml)
[![Docs Status](https://github.com/MSLNZ/msl-io/actions/workflows/docs.yml/badge.svg)](https://github.com/MSLNZ/msl-io/actions/workflows/docs.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/msl-io?logo=pypi&logoColor=gold&label=PyPI&color=blue)](https://pypi.org/project/msl-io/)
[![PyPI - Python Versions](https://img.shields.io/pypi/pyversions/msl-io.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/msl-io/)

`msl-io` follows the data model used by [HDF5] to read and write data files &mdash; where there are [Groups] and [Datasets] and each item has [Metadata]

![hdf5_data_model.png](https://raw.githubusercontent.com/MSLNZ/msl-io/main/docs/assets/images/hdf5_data_model.png)

The tree structure is similar to the file-system structure used by operating systems. [Groups] are analogous to directories (where [Root] is the root [Group]) and [Datasets] are analogous to files.

The data files that can be read or written are not restricted to [HDF5] files, but any file format that has a [Reader] implemented can be read and data files can be created using any of the [Writers].

## Install

`msl-io` is available for installation via the [Python Package Index]

```console
pip install msl-io
```

### Dependencies

* Python 3.9+
* [numpy]
* [xlrd] (bundled with `msl-io`)

## Documentation

The documentation for `msl-io` can be found [here](https://mslnz.github.io/msl-io/latest/).

[numpy]: https://www.numpy.org/
[xlrd]: https://xlrd.readthedocs.io/en/stable/
[HDF5]: https://www.hdfgroup.org/
[Root]: https://mslnz.github.io/msl-io/latest/api/base/#msl.io.base.Root
[Group]: https://mslnz.github.io/msl-io/latest/api/node/#msl.io.node.Group
[Groups]: https://mslnz.github.io/msl-io/latest/items/groups/#msl-io-group
[Datasets]: https://mslnz.github.io/msl-io/latest/items/datasets/#msl-io-dataset
[Metadata]: https://mslnz.github.io/msl-io/latest/items/metadata/#msl-io-metadata
[Reader]: https://mslnz.github.io/msl-io/latest/readers/#msl-io-readers
[Writers]: https://mslnz.github.io/msl-io/latest/writers/#msl-io-writers
[Python Package Index]: https://pypi.org/project/msl-io/