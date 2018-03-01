import logging

_readers = []

logger = logging.getLogger(__name__)


def reader(reader_class):
    def append(cls):
        _readers.append(cls)
        logger.error('registered ' + str(cls))
        return cls
    return append(reader_class)


