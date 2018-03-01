import os
import importlib
from collections import namedtuple

__author__ = 'jborbely'
__copyright__ = '\xa9 2018, ' + __author__
__version__ = '0.1.0'

version_info = namedtuple('version_info', 'major minor micro')(*map(int, __version__.split('.')[:3]))
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro) tuple."""

from . import register
from .base import Reader

# import all Reader classes that are in this directory
_ignore_list = ('__init__.py', 'base.py', 'register.py')
for file in os.listdir(os.path.dirname(__file__)):
    if file.endswith('.py') and file not in _ignore_list:
        importlib.import_module('msl.io.'+file[:-3])


def read(url, **kwargs):
    """Factory function for reading a data file.

    Parameters
    ----------
    url : :class:`str`
        The path to the file to read.
    **kwargs
        Arbitrary keyword arguments that are required by the
        :class:`~msl.io.base.Reader` subclass.

    Returns
    -------
    :class:`~msl.io.base.Dataset`
        The dataset.

    Raises
    ------
    IOError
        If the file does not exist or if no :class:`~msl.io.base.Reader`
        exists to be able to read this data file.
    """

    url = str(url)

    if not os.path.isfile(url):
        raise IOError('File does not exist ' + url)

    for reader in register._readers:
        try:
            can_read = reader.can_read(url)
        except:
            continue

        if can_read:
            r = reader(url, **kwargs)
            return r.read()

    raise IOError('No reader exists for ' + url)
