import sys
import pytest


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
        obj = lambda: pytest.skip()
    else:
        obj = lambda: None

    doctest_namespace['SKIP_IF_PYTHON_LESS_THAN_36'] = obj
