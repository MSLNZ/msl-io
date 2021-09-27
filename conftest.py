import os
import sys

import pytest
try:
    import h5py
except ImportError:
    h5py = None

from msl.io.google_api import GSheets

os.environ['MSL_IO_RUNNING_TESTS'] = 'True'


@pytest.fixture(autouse=True)
def doctest_skipif(doctest_namespace):
    # Don't want to test the output from some of the doctests if Python < 3.6
    #
    # In Python 2.7 the Dataset.__repr__ method displays the
    # shape of the ndarray. Since there is a "long" numeric type in
    # Python 2.7 the representation of the shape can have an "L" in it.
    # Therefore, we don't want to deal with the following:
    # Expected:
    #   <Dataset '/my_dataset' shape=(5,) dtype='|V16' (2 metadata)>
    # Got:
    #   <Dataset '/my_dataset' shape=(5L,) dtype='|V16' (2 metadata)>
    #
    # In Python 3.6 the order of keyword arguments is preserved
    # See PEP 468 -- Preserving the order of **kwargs
    # Therefore, we don't want to deal with the following:
    # Expected:
    #     <Metadata '/' {'one': 1, 'two': 2}>
    # Got:
    #     <Metadata '/' {'two': 2, 'one': 1}>
    if sys.version_info[:2] < (3, 6):
        ver = lambda: pytest.skip(msg='Python < 3.6')
    else:
        ver = lambda: None

    # 32-bit wheels for h5py are not available for Python 3.9+
    if h5py is None:
        h5 = lambda: pytest.skip(msg='h5py not installed')
    else:
        h5 = lambda: None

    try:
        GSheets(is_read_only=True, is_corporate_account=False)
    except:
        sheets_read_token = lambda: pytest.skip(msg='Google API tokens not available')
    else:
        sheets_read_token = lambda: None

    doctest_namespace['SKIP_IF_PYTHON_LESS_THAN_36'] = ver
    doctest_namespace['SKIP_IF_NO_H5PY'] = h5
    doctest_namespace['SKIP_IF_NO_GOOGLE_SHEETS_READ_TOKEN'] = sheets_read_token
    doctest_namespace['SKIP_RUN_AS_ADMIN'] = lambda: pytest.skip(msg='Illustrative examples')
