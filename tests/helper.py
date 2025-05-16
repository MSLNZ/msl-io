"""
Helper functions for the tests
"""
import os

import numpy as np

from msl.io import read


def read_sample(filename, **kwargs):
    """Read a file in the 'samples' directory.

    Parameters
    ----------
    filename : str
        The name of the file in the samples/ directory

    Returns
    -------
    A root object
    """
    return read(os.path.join(os.path.dirname(__file__), "samples", filename), **kwargs)


def metadata_equal(m1, m2):
    """Assert that two Metadata objects are equal."""
    assert len(m1) == len(m2)
    for k1, v1 in m1.items():
        v2 = m2[k1]
        if isinstance(v1, (list, tuple, np.ndarray)):
            assert np.array_equal(v1, v2), f"{v1}\n{v2}"
        else:
            assert v1 == v2, f"{v1} != {v2}"
    return True


def datasets_equal(d1, d2):
    """Assert that two Dataset objects are equal."""
    assert d1.name == d2.name, f"{d1.name} != {d2.name}"
    assert np.array_equal(d1.data, d2.data), f"{d1.data}\n{d2.data}"
    assert metadata_equal(d1.metadata, d2.metadata)
    return True


def roots_equal(r1, r2):
    """Assert that two Root objects are equal."""
    assert metadata_equal(r1.metadata, r2.metadata)

    groups1 = list(r1.groups())
    groups1.sort(key=lambda x: x.name)
    groups2 = list(r2.groups())
    groups2.sort(key=lambda x: x.name)
    assert len(groups1) == len(groups2)
    for g1, g2 in zip(groups1, groups2):
        assert g1.name == g2.name, f"{g1.name} != {g2.name}"
        assert metadata_equal(g1.metadata, g2.metadata)

    datasets1 = list(r1.datasets())
    datasets1.sort(key=lambda x: x.name)
    datasets2 = list(r2.datasets())
    datasets2.sort(key=lambda x: x.name)
    assert len(datasets1) == len(datasets2)
    for d1, d2 in zip(datasets1, datasets2):
        assert datasets_equal(d1, d2)

    return True
