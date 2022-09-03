# This module uses the "@" operator for matrix multiplication. The "@" operator
# was introduced in Python 3.5 and therefore this module will raise a
# SyntaxError is imported in a module < 3.5
import numpy as np

from msl.io.dataset import Dataset


def run():
    d1 = Dataset(name='d1', parent=None, read_only=True, data=[[1, 2], [3, 4]])
    d2 = Dataset(name='d2', parent=None, read_only=True, data=[[5, 6], [7, 8]])

    for rhs in ([[5, 6], [7, 8]], d2):
        result = np.matmul(d1, rhs)
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([[19, 22], [43, 50]]))

        result = d1 @ rhs
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([[19, 22], [43, 50]]))

    for lhs in ([[5, 6], [7, 8]], d2):
        result = np.matmul(lhs, d1)
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([[23, 34], [31, 46]]))

        result = lhs @ d1
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([[23, 34], [31, 46]]))
