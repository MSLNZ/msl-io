import logging

_readers = []

logger = logging.getLogger(__name__)


def reader(reader_class):
    """Use as a decorator to register a :class:`~msl.io.reader.Reader` subclass.

    Parameters
    ----------
    reader_class : :class:`~msl.io.reader.Reader`
        A :class:`~msl.io.reader.Reader` subclass.

    Returns
    -------
    :class:`~msl.io.reader.Reader`
        The :class:`~msl.io.reader.Reader`.
    """
    def append(cls):
        _readers.append(cls)
        logger.debug('registered ' + str(cls))
        return cls
    return append(reader_class)
