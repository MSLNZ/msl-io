import logging

_readers = []

logger = logging.getLogger(__name__)


def reader(reader_class):
    """Use as a decorator to register a :class:`~msl.io.base.Reader` subclass.

    Parameters
    ----------
    reader_class : :class:`~msl.io.base.Reader`
        A :class:`~msl.io.base.Reader` subclass .

    Returns
    -------
    :class:`~msl.io.base.Reader`
        The :class:`~msl.io.base.Reader`.
    """
    def append(cls):
        _readers.append(cls)
        logger.debug('registered ' + str(cls))
        return cls
    return append(reader_class)
