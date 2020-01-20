# -*- coding: utf-8 -*-
import pytest

from msl.io import read

from helper import read_sample


def test_raises_ioerror():

    # file does not exist
    with pytest.raises(IOError) as e:
        read('does_not.exist')
    assert 'File does not exist' in str(e.value)

    # no Reader class exists to read this test_read.py file
    with pytest.raises(IOError) as e:
        read(__file__)
    assert 'No Reader exists' in str(e.value)


def test_unicode_filename():
    with pytest.raises(IOError) as e:
        read_sample(u'Filé döes ñot éxist')
    assert 'File does not exist' in str(e.value)

    with pytest.raises(IOError) as e:
        read_sample(u'uñicödé')
    assert 'No Reader exists' in str(e.value)

    root = read_sample(u'uñicödé.h5')
    assert root.metadata.is_unicode
    assert root.file.endswith(u'uñicödé.h5')
    assert u'café' in root
    assert u'/café' in root
    assert u'café/caña' in root
    assert u'/café/caña' in root
    assert u'caña' in root[u'café']
    assert u'/caña' in root[u'/café']
    assert u'cafécaña' not in root
