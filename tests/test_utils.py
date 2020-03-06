import os
import re

from msl.io import (
    search,
    git_revision,
)


def test_search():

    def s(**kwargs):
        return list(search(base, **kwargs))

    # the msl-io folder
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    assert base.endswith('msl-io')

    # (?!c) means match __init__.py files but ignore __init__.pyc files
    files = s(pattern=r'__init__\.py(?!c)')
    assert len(files) == 0

    files = s(pattern=r'__init__\.py(?!c)', levels=1)
    assert len(files) == 1

    files = s(pattern=r'__init__\.py(?!c)', levels=2)
    assert len(files) == 3

    files = s(pattern=r'__init__\.py(?!c)', levels=None)
    assert len(files) == 6

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders='readers')
    assert len(files) == 5

    files = s(pattern=r'__init__\.py(?!c)', levels=None, exclude_folders=['readers', 'writers'])
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


def test_git_commit():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    sha1 = git_revision(root_dir)
    assert len(sha1) == 40
    assert all(char.isalnum() for char in sha1)

    sha1_short = git_revision(root_dir, short=True)
    assert len(sha1_short) > 0
    assert len(sha1_short) < len(sha1)
    assert sha1.startswith(sha1_short)

    # can specify any directory within the version control hierarchy
    assert git_revision(os.path.join(root_dir, '.git')) == sha1
    assert git_revision(os.path.join(root_dir, 'msl', 'examples', 'io')) == sha1
    assert git_revision(os.path.dirname(__file__)) == sha1
    assert git_revision(os.path.join(root_dir, 'docs', '_api')) == sha1
