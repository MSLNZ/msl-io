import os
import re

from msl.io import search


def test_search():

    def s(**kwargs):
        return list(search(base, **kwargs))

    # the msl-io folder
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    assert base.endswith('msl-io')

    files = s(pattern=r'__init__\.py(!?c)')
    assert len(files) == 0

    files = s(pattern=r'__init__\.py(!?c)', levels=1)
    assert len(files) == 1

    files = s(pattern=r'__init__\.py(!?c)', levels=2)
    assert len(files) == 3

    files = s(pattern=r'__init__\.py(!?c)', levels=None)
    assert len(files) == 6

    files = s(pattern=r'__init__\.py(!?c)', levels=None, exclude_folders='readers')
    assert len(files) == 5

    files = s(pattern=r'__init__\.py(!?c)', levels=None, exclude_folders=['readers', 'writers'])
    assert len(files) == 4

    files = s(pattern=r'authors')
    assert len(files) == 0

    files = s(pattern=r'authors', regex_flags=re.IGNORECASE)
    assert len(files) == 1

    files = s(pattern=r'setup')
    assert len(files) == 2

    files = s(pattern=r'README', levels=None)
    assert len(files) == 1

    files = s(pattern=r'README', levels=None, ignore_hidden_folders=False, exclude_folders=['.eggs', '.pytest_cache', '.cache'])
    assert len(files) == 1

    files = s(pattern=r'(^in|^auth)', levels=1, exclude_folders='htmlcov')
    assert len(files) == 3

    files = s(pattern=r'(^in|^auth)', levels=1, regex_flags=re.IGNORECASE, exclude_folders='htmlcov')
    assert len(files) == 4
