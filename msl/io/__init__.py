import os
import importlib
from collections import namedtuple

from . import register
from .reader import Reader

__author__ = 'jborbely'
__copyright__ = '\xa9 2018, ' + __author__
__version__ = '0.1.0'

version_info = namedtuple('version_info', 'major minor micro')(*map(int, __version__.split('.')[:3]))
""":obj:`~collections.namedtuple`: Contains the version information as a (major, minor, micro) tuple."""

# import all Reader classes that are in the "readers" directory
for file in os.listdir(os.path.dirname(__file__) + '/readers'):
    if file.endswith('.py') and file != '__init__.py':
        importlib.import_module('msl.io.'+file[:-3])


def read(url, **kwargs):
    """Factory function for reading a data file.

    Parameters
    ----------
    url : :class:`str`
        The path to the file to read.
    **kwargs
        Arbitrary keyword arguments that are required by the
        :class:`~msl.io.reader.Reader` subclass.

    Returns
    -------
    :class:`~msl.io.root.Root`
        The root object.

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
