import os
import re

from msl.io import search


def test_find_files():

    def ff(**kwargs):
        return list(search(base, **kwargs))

    # the msl-io folder
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    assert base.endswith('msl-io')

    files = ff(pattern=r'__init__\.py(!?c)')
    assert len(files) == 0

    files = ff(pattern=r'__init__\.py(!?c)', levels=1)
    assert len(files) == 1

    files = ff(pattern=r'__init__\.py(!?c)', levels=2)
    assert len(files) == 3

    files = ff(pattern=r'__init__\.py(!?c)', levels=None)
    assert len(files) == 5

    files = ff(pattern=r'__init__\.py(!?c)', levels=None, exclude_folders='readers')
    assert len(files) == 4

    files = ff(pattern=r'authors')
    assert len(files) == 0

    files = ff(pattern=r'authors', regex_flags=re.IGNORECASE)
    assert len(files) == 1

    files = ff(pattern=r'setup')
    assert len(files) == 2

    files = ff(pattern=r'README', levels=None)
    assert len(files) == 1

    files = ff(pattern=r'README', levels=None, ignore_hidden_folders=False, exclude_folders='.eggs')
    assert len(files) == 2, 'We need the .pytest_cache/ folder to exist... Rerun tests!'

    files = ff(pattern=r'README', levels=None, ignore_hidden_folders=False, exclude_folders=['.eggs', '.pytest_cache', '.cache'])
    assert len(files) == 1

    files = ff(pattern=r'(^in|^auth)', levels=1, exclude_folders='htmlcov')
    assert len(files) == 3

    files = ff(pattern=r'(^in|^auth)', levels=1, regex_flags=re.IGNORECASE, exclude_folders='htmlcov')
    assert len(files) == 4
