import os
import logging
import tempfile

import pytest
import numpy as np
import h5py

from msl.io import JSONWriter, HDF5Writer, read
from msl.io.dataset_logging import DatasetLogging

logger = logging.getLogger(__name__)

num_initial_handlers = 0


def setup_module():
    # Set the initial number of logging handlers.
    # Since pytest has its own this setup() function must be called
    # when pytest begins to test this module
    global num_initial_handlers
    num_initial_handlers = len(logging.getLogger().handlers)


def test_create():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    # also checks that specifying the level as a int is okay
    dset = root.create_dataset_logging('log', level=logging.INFO)

    assert dset.name == '/log'
    assert root.is_dataset(dset)
    assert isinstance(dset, DatasetLogging)
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1
    assert len(dset) == 0
    assert np.array_equal(dset.dtype.names, ('asctime', 'levelname', 'name', 'message'))
    assert len(dset.metadata) == 3
    assert dset.metadata['logging_level'] == logging.INFO
    assert dset.metadata.logging_level_name == 'INFO'
    assert dset.metadata.logging_date_format == '%Y-%m-%dT%H:%M:%S.%f'

    logger.debug('hello')
    logger.info('world')
    logger.warning('foo')
    logger.error('bar')

    assert len(dset) == 3
    assert dset[ dset['levelname'] == 'ERROR']['message'] == 'bar'

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_create_and_require():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    dset = root.create_dataset_logging('/a/b/log', level=logging.DEBUG)

    assert dset.name == '/a/b/log'
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

    with pytest.raises(ValueError):
        root.create_dataset_logging(dset.name)
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

    assert not dset.is_read_only
    assert root.is_dataset(dset)
    assert len(dset.metadata) == 3
    assert dset.metadata.logging_level == logging.DEBUG
    assert dset.metadata['logging_level_name'] == 'DEBUG'
    assert dset.metadata.logging_date_format == '%Y-%m-%dT%H:%M:%S.%f'

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

    assert len(dset) == 5
    assert np.array_equal(dset['levelname'], ['DEBUG', 'WARNING', 'INFO', 'CRITICAL', 'ERROR'])
    assert np.array_equal(dset['message'], messages)

    b = root.a.b
    dset2 = b.require_dataset_logging('log')
    assert dset2 is dset

    logger.info('another info message')
    assert np.array_equal(dset['levelname'], ['DEBUG', 'WARNING', 'INFO', 'CRITICAL', 'ERROR', 'INFO'])
    assert np.array_equal(dset['message'], messages + ['another info message'])

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_create_multiple_same_root():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    dset1 = root.create_dataset_logging('log')

    assert dset1.name == '/log'
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

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

    assert len(logging.getLogger().handlers) == num_initial_handlers + 2

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

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_requires_failures():
    assert len(logging.getLogger().handlers) == num_initial_handlers

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
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_filter_loggers():
    assert len(logging.getLogger().handlers) == num_initial_handlers

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
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_save_then_read():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    json = JSONWriter(file=os.path.join(tempfile.gettempdir(), 'msl-io-junk.json'))
    h5 = HDF5Writer(file=os.path.join(tempfile.gettempdir(), 'msl-io-junk.h5'))

    json.create_dataset_logging('log', date_fmt='%H:%M:%S', extra='ABC')
    h5.require_dataset_logging('/a/b/c/d/e/log')  # doesn't exist so creates it

    assert isinstance(json.log, DatasetLogging)
    assert isinstance(h5.a.b.c.d.e.log, DatasetLogging)

    logger.info('hello %s', 'world')
    logger.warning('foo')

    json.write(mode='w')
    h5.write(mode='w')

    json_2 = read(json.file)
    h5_2 = read(h5.file)
    os.remove(json.file)
    os.remove(h5.file)

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

    assert len(json_2.log.metadata) == 4
    assert json_2.log.metadata['extra'] == 'ABC'
    assert json_2.log.metadata['logging_level'] == logging.INFO
    assert json_2.log.metadata.logging_level_name == 'INFO'
    assert json_2.log.metadata.logging_date_format == '%H:%M:%S'

    assert len(h5_2.a.b.c.d.e.log.metadata) == 3
    assert h5_2.a.b.c.d.e.log.metadata['logging_level'] == logging.INFO
    assert h5_2.a.b.c.d.e.log.metadata.logging_level_name == 'INFO'
    assert h5_2.a.b.c.d.e.log.metadata.logging_date_format == '%Y-%m-%dT%H:%M:%S.%f'

    assert np.array_equal(json_2.log['message'], ['hello world', 'foo'])
    if h5py.version.version_tuple.major < 3:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'],
            ['hello world', 'foo']
        )
    else:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'],
            [b'hello world', b'foo']
        )

    json.log.remove_handler()

    logger.info('baz')
    assert np.array_equal(json.log['message'], ['hello world', 'foo'])
    assert np.array_equal(h5.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz'])
    assert np.array_equal(json_2.log['message'], ['hello world', 'foo', 'baz'])
    if h5py.version.version_tuple.major < 3:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'],
            ['hello world', 'foo', 'baz']
        )
    else:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'].tolist(),
            [b'hello world', b'foo', 'baz']
        )

    h5.a.b.c.d.e.log.remove_handler()

    logger.warning('ooops...')
    logger.error('YIKES!')
    assert np.array_equal(json.log['message'], ['hello world', 'foo'])
    assert np.array_equal(h5.a.b.c.d.e.log['message'], ['hello world', 'foo', 'baz'])
    assert np.array_equal(json_2.log['message'], ['hello world', 'foo', 'baz', 'ooops...', 'YIKES!'])
    if h5py.version.version_tuple.major < 3:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'],
            ['hello world', 'foo', 'baz', 'ooops...', 'YIKES!']
        )
    else:
        assert np.array_equal(
            h5_2.a.b.c.d.e.log['message'].tolist(),
            [b'hello world', b'foo', 'baz', 'ooops...', 'YIKES!']
        )

    json_2.log.remove_handler()
    h5_2.a.b.c.d.e.log.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_all_attributes():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    attributes = [
        'asctime', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'message', 'module', 'msecs', 'name', 'pathname',
        'process', 'processName', 'relativeCreated', 'thread', 'threadName'
    ]

    json = JSONWriter()

    c = json.create_group('a/b/c')
    dset = c.create_dataset_logging('/d/e/f/log', level='DEBUG', attributes=attributes)

    assert dset.name == '/a/b/c/d/e/f/log'

    e = json.a.b.c.d.e
    dset2 = e.require_dataset_logging('/f/log')
    assert dset2 is dset

    logger.debug('d e b u g')
    logger.info('i n f o')
    logger.warning('w a r n i n g')
    logger.error('e r r o r')
    logger.critical('c r i t i c a l')

    assert len(dset) == 5
    assert len(dset[dset['levelno'] > logging.DEBUG]) == 4
    assert len(dset[dset['levelno'] > logging.INFO]) == 3
    assert len(dset[dset['levelno'] > logging.WARNING]) == 2
    assert len(dset[dset['levelno'] > logging.ERROR]) == 1
    assert len(dset[dset['levelno'] > logging.CRITICAL]) == 0
    assert np.array_equal(dset.dtype.names, attributes)

    dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_is_logging_dataset():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    root.create_dataset('/a/b/regular')
    root.create_dataset_logging('log')
    root.create_dataset('regular')
    root.create_dataset_logging('/a/b/log')
    root.create_dataset_logging('/a/b/log2')

    log_dsets = [dset for dset in root.datasets() if root.is_dataset_logging(dset)]

    assert len(list(root.items())) == 7
    assert len(list(root.descendants())) == 2
    assert len(list(root.datasets())) == 5
    assert len(log_dsets) == 3

    assert len(logging.getLogger().handlers) == num_initial_handlers + 3

    for dset in root.datasets():
        if root.is_dataset_logging(dset):
            dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_invalid_attributes():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    # cannot be an empty list/tuple
    with pytest.raises(ValueError):
        root.create_dataset_logging('log', attributes=[])
    with pytest.raises(ValueError):
        root.create_dataset_logging('log', attributes=tuple())

    # every element must be a string
    with pytest.raises(ValueError):
        root.create_dataset_logging('log', attributes=[1, 2, 3])
    with pytest.raises(ValueError):
        root.create_dataset_logging('log', attributes=['1', '2', 3])

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_initial_shape():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    num_records = 1234

    log1 = root.create_dataset_logging('log1', shape=(10000,))
    log2 = root.create_dataset_logging('log2')
    log3 = root.create_dataset_logging('log3', size=256)
    log4 = root.create_dataset_logging('log4', size=0)

    # the shape is an argument of Dataset and does not get passed to the Metadata
    assert 'shape' not in log1.metadata

    # specifying the `size` gets popped from the kwarg and gets converted to a `shape` kwarg
    assert 'size' not in log3.metadata
    assert 'shape' not in log3.metadata

    assert len(logging.getLogger().handlers) == num_initial_handlers + 4

    assert len(log1) == 10000
    assert len(log2) == 0
    assert len(log3) == 256
    assert len(log4) == 0

    for i in range(num_records):
        logging.info(i)  # just to be different, use the root logger

    assert len(log1) == 10000
    assert len(log2) == num_records
    assert len(log3) == 1380
    assert len(log4) == 1267

    for dset in root.datasets():
        dset.remove_empty_rows()

    assert len(log1) == num_records
    assert len(log2) == num_records
    assert len(log3) == num_records
    assert len(log4) == num_records

    for i in range(num_records):
        assert int(log1[i][3]) == i
        assert int(log2[i][3]) == i
        assert int(log3[i][3]) == i
        assert int(log4[i][3]) == i

    for dset in root.datasets():
        dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_initial_index_value():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter(file=os.path.join(tempfile.gettempdir(), 'msl-io-junk.json'))
    root.create_dataset_logging('log')

    n = 10

    for i in range(n):
        logger.info('message %d', i)

    assert len(root.log) == n

    root.write(mode='w')

    root2 = read(root.file)
    root3 = read(root.file)

    # specify more than n elements
    root2.require_dataset_logging(root.log.name, size=n+5)

    # specify less than n elements which automatically gets increased to n
    # also specify shape as an integer which gets cast to a 1-d tuple
    root3.require_dataset_logging(root.log.name, shape=n-5)

    assert len(logging.getLogger().handlers) == num_initial_handlers + 3

    os.remove(root.file)

    assert root2.log.size == n+5
    assert root3.log.size == n  # gets increased to n

    root.log.remove_handler()
    for i in range(n, 2*n):
        logger.info('message %d', i)

    assert root.log.size == n
    assert root2.log.size == 24
    assert root3.log.size == 27

    root.log.remove_empty_rows()
    root2.log.remove_empty_rows()
    root3.log.remove_empty_rows()

    assert root.log.size == n
    assert root2.log.size == 2*n
    assert root3.log.size == 2*n

    root2.log.remove_handler()
    for i in range(2*n, 3*n):
        logger.info('message %d', i)

    assert root.log.size == n
    assert root2.log.size == 2*n
    assert root3.log.size == 39

    root.log.remove_empty_rows()
    root2.log.remove_empty_rows()
    root3.log.remove_empty_rows()

    assert root.log.size == n
    assert root2.log.size == 2*n
    assert root3.log.size == 3*n

    messages1 = root['log']['message']
    messages2 = root2['log']['message']
    messages3 = root3['log']['message']
    for i in range(3*n):
        if i < n:
            assert messages1[i] == 'message %d' % i
        if i < 2*n:
            assert messages2[i] == 'message %d' % i
        assert messages3[i] == 'message %d' % i

    root3['log'].remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_invalid_shape_or_size():
    root = JSONWriter()

    with pytest.raises(ValueError) as err:
        root.create_dataset_logging('log', shape=())
    assert str(err.value).startswith('Invalid shape')

    with pytest.raises(ValueError) as err:
        root.create_dataset_logging('log', shape=[])
    assert str(err.value).startswith('Invalid shape')

    with pytest.raises(ValueError) as err:
        root.create_dataset_logging('log', shape=(10, 5))
    assert str(err.value).startswith('Invalid shape')

    with pytest.raises(ValueError) as err:
        root.create_dataset_logging('log', shape=(-1,))
    assert str(err.value).startswith('Invalid shape')

    with pytest.raises(ValueError) as err:
        root.create_dataset_logging('log', size=-1)
    assert str(err.value).startswith('Invalid shape')

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_set_logger():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    root.create_dataset_logging('log')

    for obj in [None, 'no', JSONWriter, logging.INFO, logging.Formatter, logging.Handler]:
        with pytest.raises(TypeError) as err:
            root.log.set_logger(obj)
        assert str(err.value) == 'Must be a logging.Logger object'

    root.log.set_logger(logger)
    root.log.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_hash():
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    root.create_dataset_logging('log')

    # just tests that a hash value exists, don't care about the actual value
    assert isinstance(hash(root.log), int)

    root.log.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers
