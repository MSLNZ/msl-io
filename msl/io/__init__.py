import os
from collections import namedtuple

__author__ = 'jborbely'
__copyright__ = '\xa9 2018, ' + __author__
__version__ = '0.1.0'

version_info = namedtuple('version_info', 'major minor micro')(*map(int, __version__.split('.')[:3]))
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro) tuple."""

from .base import Reader
from . import register

from .register import _readers

def read(url, **kwargs):

    url = str(url)

    if not os.path.isfile(url):
        raise IOError('File does not exist '  + str(url))

    # factory method
    for reader in _readers:
        try:
            can_read = reader.can_read(url)
        except:
            continue

        if can_read:
            r = reader(url, **kwargs)
            return r.read()

    raise IOError("No reader exists to read " + url)



from .csv import CSV
