import pytest

from msl.io import read


def test_raises_ioerror():

    # file does not exist
    with pytest.raises(IOError) as e:
        read('does_not.exist')
    assert 'File does not exist' in str(e)

    # no Reader class exists to read this test_read.py file
    with pytest.raises(IOError) as e:
        read(__file__)
    assert 'No Reader exists' in str(e)
