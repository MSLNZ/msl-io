"""
Helper functions for the tests
"""
import os

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
    return read(os.path.join(os.path.dirname(__file__), 'samples', filename), **kwargs)
