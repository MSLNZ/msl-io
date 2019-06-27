import logging

_readers = []

logger = logging.getLogger(__name__)


def register(reader_class):
    """Use as a decorator to register a :class:`~msl.io.base_io.Reader` subclass.

    Parameters
    ----------
    reader_class : :class:`~msl.io.base_io.Reader`
        A :class:`~msl.io.base_io.Reader` subclass.

    Returns
    -------
    :class:`~msl.io.base_io.Reader`
        The :class:`~msl.io.base_io.Reader`.
    """
    def append(cls):
        _readers.append(cls)
        logger.debug('registered {!r}'.format(cls))
        return cls
    return append(reader_class)
