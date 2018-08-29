"""
Helper functions for the tests
"""
import os

from msl.io import read as _io_read


def read_sample(filename, **kwargs):
    """Read the file in the samples directory

    Parameters
    ----------
    filename : str
        The name of the file in the samples/ directory

    Returns
    -------
    msl.io.root.Root
        The root object
    """
    return _io_read(os.path.join(os.path.dirname(__file__), 'samples', filename), **kwargs)
