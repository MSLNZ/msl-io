import os
import logging
import tempfile

import pytest
import numpy as np

from msl.io import JSONWriter, HDF5Writer, read
from msl.io.dataset_logging import DatasetLogging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)


def test_create():
    assert len(logging.getLogger().handlers) == 2

    root = JSONWriter()

    # also checks that specifying the level as a int is okay
    dset = root.create_dataset_logging('log', level=logging.INFO)

    assert dset.name == '/log'
    assert root.is_dataset(dset)
    assert isinstance(dset, DatasetLogging)
    assert len(logging.getLogger().handlers) == 3
    assert len(dset) == 0
    assert np.array_equal(dset.dtype.names, ('asctime', 'levelname', 'name', 'message'))
    assert dset.metadata['logging_level'] == logging.INFO
    assert dset.metadata.logging_level_name == 'INFO'

    logger.debug('hello')
    logger.info('world')
    logger.warning('foo')
    logger.error('bar')

    assert len(dset) == 3
    assert dset[ dset['levelname'] == 'ERROR']['message'] == 'bar'

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == 2


def test_create_and_require():
    assert len(logging.getLogger().handlers) == 2

    root = JSONWriter()
    dset = root.create_dataset_logging('/a/b/log', level=logging.DEBUG)

    assert dset.name == '/a/b/log'
    assert len(logging.getLogger().handlers) == 3

    with pytest.raises(ValueError):
        root.create_dataset_logging(dset.name)
    assert len(logging.getLogger().handlers) == 3

    assert not dset.is_read_only
    assert root.is_dataset(dset)
    assert len(dset.metadata) == 2
    assert dset.metadata.logging_level == logging.DEBUG
    assert dset.metadata['logging_level_name'] == 'DEBUG'

    messages = [
        'a debug message',
        'you should not do that so please be careful!',
        'tell me something useful',
        'NO!!!',
        'this is an error, cannot do that'
    ]

    logger.debug(messages[0])
    logger.warning(messages[1])
    logger.info(messages[2])
    logger.critical(messages[3])
    logger.error(messages[4])

    assert len(dset) == 5, dset
    assert np.array_equal(dset['levelname'], ['DEBUG', 'WARNING', 'INFO', 'CRITICAL', 'ERROR'])
    assert np.array_equal(dset['message'], messages)

    b = root.a.b
    dset2 = b.require_dataset_logging('log')
    assert dset2 is dset

    logger.info('another info message')
    assert np.array_equal(dset['levelname'], ['DEBUG', 'WARNING', 'INFO', 'CRITICAL', 'ERROR', 'INFO'])
    assert np.array_equal(dset['message'], messages + ['another info message'])

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == 2


def test_create_multiple_same_root():
    assert len(logging.getLogger().handlers) == 2

    root = JSONWriter()
    dset1 = root.create_dataset_logging('log')

    assert dset1.name == '/log'
    assert len(logging.getLogger().handlers) == 3

    messages = [
        'a debug message',
        'you should not do that so please be careful!',
        'tell me something useful',
        'NO!!!',
        'this is an error, cannot do that'
    ]

    logger.debug(messages[0])
    logger.warning(messages[1])

    xx = root.create_group('xx')
    dset2 = xx.create_dataset_logging('log', level=logging.WARNING, attributes=['funcName', 'levelno'])
    assert dset2.name == '/xx/log'

    assert len(logging.getLogger().handlers) == 4

    logger.info(messages[2])
    logger.critical(messages[3])
    logger.error(messages[4])

    assert dset1.level == logging.INFO
    assert len(dset1) == 4  # the DEBUG message is not there
    assert np.array_equal(dset1['levelname'], ['WARNING', 'INFO', 'CRITICAL', 'ERROR'])
    assert np.array_equal(dset1['message'], messages[1:])

    assert dset2.level == logging.WARNING
    assert len(dset2) == 2  # only ERROR and CRITICAL messages are there
    assert np.array_equal(dset2['levelno'], [logging.CRITICAL, logging.ERROR])
    assert np.array_equal(dset2['funcName'], ['test_create_multiple_same_root'] * 2)

    dset1.remove_handler()
    dset2.remove_handler()

    assert len(logging.getLogger().handlers) == 2


def test_requires_failures():
    assert len(logging.getLogger().handlers) == 2

    root = JSONWriter()
    root.create_dataset('regular')
    root.create_dataset_logging('logging')

    assert np.array_equal(root.logging.dtype.names, ['asctime', 'levelname', 'name', 'message'])
    with pytest.raises(ValueError) as err:
        root.require_dataset_logging('logging', attributes=['lineno', 'filename'])
    assert str(err.value).endswith("does not equal ('lineno', 'filename')")

    with pytest.raises(ValueError) as err:
        root.require_dataset_logging('regular')
    assert str(err.value).endswith('not used for logging')

    root.logging.remove_handler()
    assert len(logging.getLogger().handlers) == 2


def test_filter_loggers():
    assert len(logging.getLogger().handlers) == 2

    unlogger = logging.getLogger('unwanted')

    root = JSONWriter()
    dset = root.create_dataset_logging('log')
    dset.addFilter(logging.Filter(__name__))

    logger.info('ok')
    unlogger.info('not in dataset')

    assert len(dset) == 1
    assert dset['message'] == 'ok'

    dset.remove_handler()
    del logging.Logger.manager.loggerDict['unwanted']
    assert len(logging.getLogger().handlers) == 2


def test_save_then_read():
    assert len(logging.getLogger().handlers) == 2

    json = JSONWriter(url=os.path.join(tempfile.gettempdir(), 'msl-io-junk.json'))
    h5 = HDF5Writer(url=os.path.join(tempfile.gettempdir(), 'msl-io-junk.h5'))

    json.create_dataset_logging('log', extra='ABC')
    h5.require_dataset_logging('/a/b/c/d/e/log')  # doesn't exist so creates it

    assert isinstance(json.log, DatasetLogging)
    assert isinstance(h5.a.b.c.d.e.log, DatasetLogging)

    logger.info('hello %s', 'world')
    logger.warning('foo')

    json.write(mode='w')
    h5.write(mode='w')

    json_2 = read(json.url)
    h5_2 = read(h5.url)
    os.remove(json.url)
    os.remove(h5.url)

    # when a file is read, what was once a DatasetLogging object is loaded as a regular Dataset
    # but can be turned back into a DatasetLogging by calling require_dataset_logging()
    assert not isinstance(json_2.log, DatasetLogging)
    assert not isinstance(h5_2.a.b.c.d.e.log, DatasetLogging)
    assert json_2.is_dataset(json_2.log)
    assert h5_2.is_dataset(h5_2.a.b.c.d.e.log)

    # convert the Dataset to DatasetLogging
    json_2.require_dataset_logging(json_2.log.name)
    h5_2.a.b.c.require_dataset_logging('/d/e/log')
    assert isinstance(json_2.log, DatasetLogging)
    assert isinstance(h5_2.a.b.c.d.e.log, DatasetLogging)
    assert json_2.is_dataset(json_2.log)
    assert h5_2.is_dataset(h5_2.a.b.c.d.e.log)

    assert len(json_2.log.metadata) == 3
    assert json_2.log.metadata['extra'] == 'ABC'
    assert json_2.log.metadata['logging_level'] == logging.INFO
    assert json_2.log.metadata.logging_level_name == 'INFO'

    assert len(h5_2.a.b.c.d.e.log.metadata) == 2
    assert h5_2.a.b.c.d.e.log.metadata['logging_level'] == logging.INFO
    assert h5_2.a.b.c.d.e.log.metadata.logging_level_name == 'INFO'

    assert np.array_equal(json_2.log['message'], ['hello world', 'foo'])
    assert np.array_equal(h5_2.a.b.c.d.e.log['message'], ['hello world', 'foo'])

    json.log.remove_handler()

    logger.info('baz')
    assert np.array_equal(json.log['message'], ['hello world', 'foo'])
    assert np.array_equal(h5.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz'])
    assert np.array_equal(json_2.log['message'], ['hello world', 'foo', 'baz'])
    assert np.array_equal(h5_2.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz'])

    h5.a.b.c.d.e.log.remove_handler()

    logger.warning('ooops...')
    logger.error('YIKES!')
    assert np.array_equal(json.log['message'], ['hello world', 'foo'])
    assert np.array_equal(h5.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz'])
    assert np.array_equal(json_2.log['message'], ['hello world', 'foo', 'baz', 'ooops...', 'YIKES!'])
    assert np.array_equal(h5_2.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz', 'ooops...', 'YIKES!'])

    json_2.log.remove_handler()
    h5_2.a.b.c.d.e.log.remove_handler()

    assert len(logging.getLogger().handlers) == 2
