import logging
import tempfile
from pathlib import Path

import numpy as np
import pytest

try:
    import h5py  # type: ignore[import-untyped] # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    h5py = None

from msl.io import DatasetLogging, HDF5Writer, JSONWriter, read

logger = logging.getLogger(__name__)

num_initial_handlers = 0


def setup_module() -> None:
    # Set the initial number of logging handlers.
    # Since pytest has its own this setup() function must be called
    # when pytest begins to test this module
    global num_initial_handlers  # noqa: PLW0603
    num_initial_handlers = len(logging.getLogger().handlers)


def test_create() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    # also checks that specifying the level as a int is okay
    dset = root.create_dataset_logging("log", level=logging.INFO)

    assert dset.name == "/log"
    assert root.is_dataset(dset)
    assert isinstance(dset, DatasetLogging)
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1
    assert len(dset) == 0
    assert np.array_equal(dset.dtype.names, ("asctime", "levelname", "name", "message"))
    assert len(dset.metadata) == 3
    assert dset.metadata["logging_level"] == logging.INFO
    assert dset.metadata.logging_level_name == "INFO"
    assert dset.metadata.logging_date_format == "%Y-%m-%dT%H:%M:%S.%f"

    logger.debug("hello")
    logger.info("world")
    logger.warning("foo")
    logger.error("bar")

    assert len(dset) == 3
    assert dset[dset["levelname"] == "ERROR"]["message"] == "bar"

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_create_and_require() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    dset = root.create_dataset_logging("/a/b/log", level=logging.DEBUG)

    assert dset.name == "/a/b/log"
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

    with pytest.raises(ValueError, match=r"not unique"):
        _ = root.create_dataset_logging(dset.name)
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

    assert not dset.read_only
    assert root.is_dataset(dset)
    assert len(dset.metadata) == 3
    assert dset.metadata.logging_level == logging.DEBUG
    assert dset.metadata["logging_level_name"] == "DEBUG"
    assert dset.metadata.logging_date_format == "%Y-%m-%dT%H:%M:%S.%f"

    messages = [
        "a debug message",
        "you should not do that so please be careful!",
        "tell me something useful",
        "NO!!!",
        "this is an error, cannot do that",
    ]

    logger.debug(messages[0])
    logger.warning(messages[1])
    logger.info(messages[2])
    logger.critical(messages[3])
    logger.error(messages[4])

    assert len(dset) == 5
    assert np.array_equal(dset["levelname"], ["DEBUG", "WARNING", "INFO", "CRITICAL", "ERROR"])
    assert np.array_equal(dset["message"], messages)

    b = root.a.b
    dset2 = b.require_dataset_logging("log")
    assert dset2 is dset

    logger.info("another info message")
    assert np.array_equal(dset["levelname"], ["DEBUG", "WARNING", "INFO", "CRITICAL", "ERROR", "INFO"])
    assert np.array_equal(dset["message"], [*messages, "another info message"])

    dset.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_create_multiple_same_root() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    dset1 = root.create_dataset_logging("log")

    assert dset1.name == "/log"
    assert len(logging.getLogger().handlers) == num_initial_handlers + 1

    messages = [
        "a debug message",
        "you should not do that so please be careful!",
        "tell me something useful",
        "NO!!!",
        "this is an error, cannot do that",
    ]

    logger.debug(messages[0])
    logger.warning(messages[1])

    xx = root.create_group("xx")
    dset2 = xx.create_dataset_logging("log", level=logging.WARNING, attributes=["funcName", "levelno"])
    assert dset2.name == "/xx/log"

    assert len(logging.getLogger().handlers) == num_initial_handlers + 2

    logger.info(messages[2])
    logger.critical(messages[3])
    logger.error(messages[4])

    assert dset1.level == logging.INFO
    assert len(dset1) == 4  # the DEBUG message is not there
    assert np.array_equal(dset1["levelname"], ["WARNING", "INFO", "CRITICAL", "ERROR"])
    assert np.array_equal(dset1["message"], messages[1:])

    assert dset2.level == logging.WARNING
    assert len(dset2) == 2  # only ERROR and CRITICAL messages are there
    assert np.array_equal(dset2["levelno"], [logging.CRITICAL, logging.ERROR])
    assert np.array_equal(dset2["funcName"], ["test_create_multiple_same_root"] * 2)

    dset1.remove_handler()
    dset2.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_requires_failures() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    _ = root.create_dataset("regular")
    _ = root.create_dataset_logging("logging")

    assert np.array_equal(root.logging.dtype.names, ["asctime", "levelname", "name", "message"])  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match=r"does not equal \('lineno', 'filename'\)"):
        _ = root.require_dataset_logging("logging", attributes=["lineno", "filename"])

    with pytest.raises(ValueError, match=r"not used for logging"):
        _ = root.require_dataset_logging("regular")

    assert isinstance(root.logging, DatasetLogging)
    root.logging.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_filter_loggers() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    un_logger = logging.getLogger("unwanted")

    root = JSONWriter()
    dset = root.create_dataset_logging("log")
    dset.add_filter(logging.Filter(__name__))

    logger.info("ok")
    un_logger.info("not in dataset")

    assert len(dset) == 1
    assert dset["message"] == "ok"

    dset.remove_handler()
    del logging.Logger.manager.loggerDict["unwanted"]
    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_save_then_read() -> None:  # noqa: C901, PLR0912, PLR0915
    assert len(logging.getLogger().handlers) == num_initial_handlers

    json = JSONWriter(file=Path(tempfile.gettempdir()) / "msl-io-junk.json")
    h5 = HDF5Writer(file=Path(tempfile.gettempdir()) / "msl-io-junk.h5")

    _ = json.create_dataset_logging("log", date_fmt="%H:%M:%S", extra="ABC")
    _ = h5.require_dataset_logging("/a/b/c/d/e/log")  # doesn't exist so creates it

    assert isinstance(json.log, DatasetLogging)
    assert isinstance(h5.a.b.c.d.e.log, DatasetLogging)

    logger.info("hello %s", "world")
    logger.warning("foo")

    json.write(mode="w")
    if h5py is not None:
        h5.write(mode="w")

    assert isinstance(json.file, Path)
    assert isinstance(h5.file, Path)

    json_2 = read(json.file)
    if h5py is not None:
        h5_2 = read(h5.file)
        Path(h5.file).unlink()
    else:
        h5_2 = None
    Path(json.file).unlink()

    # when a file is read, what was once a DatasetLogging object is loaded as a regular Dataset
    # but can be turned back into a DatasetLogging by calling require_dataset_logging()
    assert not isinstance(json_2.log, DatasetLogging)
    if h5_2 is not None:
        assert not isinstance(h5_2.a.b.c.d.e.log, DatasetLogging)
    assert json_2.is_dataset(json_2.log)
    if h5_2 is not None:
        assert h5_2.is_dataset(h5_2.a.b.c.d.e.log)

    # convert the Dataset to DatasetLogging
    _ = json_2.require_dataset_logging(json_2.log.name)
    if h5_2 is not None:
        _ = h5_2.a.b.c.require_dataset_logging("/d/e/log")
    assert isinstance(json_2.log, DatasetLogging)
    if h5_2 is not None:
        assert isinstance(h5_2.a.b.c.d.e.log, DatasetLogging)
    assert json_2.is_dataset(json_2.log)
    if h5_2 is not None:
        assert h5_2.is_dataset(h5_2.a.b.c.d.e.log)

    assert len(json_2.log.metadata) == 4
    assert json_2.log.metadata["extra"] == "ABC"
    assert json_2.log.metadata["logging_level"] == logging.INFO
    assert json_2.log.metadata.logging_level_name == "INFO"
    assert json_2.log.metadata.logging_date_format == "%H:%M:%S"

    if h5_2 is not None:
        assert len(h5_2.a.b.c.d.e.log.metadata) == 3
        assert h5_2.a.b.c.d.e.log.metadata["logging_level"] == logging.INFO
        assert h5_2.a.b.c.d.e.log.metadata.logging_level_name == "INFO"
        assert h5_2.a.b.c.d.e.log.metadata.logging_date_format == "%Y-%m-%dT%H:%M:%S.%f"

    assert np.array_equal(json_2.log["message"], ["hello world", "foo"])
    if h5_2 is not None:
        assert np.array_equal(h5_2.a.b.c.d.e.log["message"], [b"hello world", b"foo"])  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

    json.log.remove_handler()

    logger.info("baz")
    assert np.array_equal(json.log["message"], ["hello world", "foo"])
    assert np.array_equal(h5.a.b.c.d.e.log["message"], ["hello world", "foo", "baz"])
    assert np.array_equal(json_2.log["message"], ["hello world", "foo", "baz"])
    if h5_2 is not None:
        assert np.array_equal(h5_2.a.b.c.d.e.log["message"].tolist(), [b"hello world", b"foo", "baz"])  # type: ignore[arg-type, operator] # pyright: ignore[reportCallIssue, reportUnknownArgumentType]

    h5.a.b.c.d.e.log.remove_handler()

    logger.warning("ooops...")  # cSpell: ignore ooops
    logger.error("YIKES!")
    assert np.array_equal(json.log["message"], ["hello world", "foo"])
    assert np.array_equal(h5.a.b.c.d.e.log["message"], ["hello world", "foo", "baz"])
    assert np.array_equal(json_2.log["message"], ["hello world", "foo", "baz", "ooops...", "YIKES!"])
    if h5_2 is not None:
        assert isinstance(h5_2.a.b.c.d.e.log["message"], np.ndarray)
        assert np.array_equal(
            h5_2.a.b.c.d.e.log["message"].tolist(),  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
            [b"hello world", b"foo", "baz", "ooops...", "YIKES!"],  # type: ignore[arg-type]
        )

    json_2.log.remove_handler()
    if h5_2 is not None:
        assert isinstance(h5_2.a.b.c.d.e.log, DatasetLogging)
        h5_2.a.b.c.d.e.log.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_all_attributes() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    attributes = [
        "asctime",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",  # cSpell: ignore msecs
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
    ]

    json = JSONWriter()

    c = json.create_group("a/b/c")
    dset = c.create_dataset_logging("/d/e/f/log", level="DEBUG", attributes=attributes)

    assert dset.name == "/a/b/c/d/e/f/log"

    e = json.a.b.c.d.e
    dset2 = e.require_dataset_logging("/f/log")
    assert dset2 is dset

    logger.debug("d e b u g")
    logger.info("i n f o")
    logger.warning("w a r n i n g")
    logger.error("e r r o r")
    logger.critical("c r i t i c a l")

    assert len(dset) == 5
    assert len(dset[dset["levelno"] > logging.DEBUG]) == 4
    assert len(dset[dset["levelno"] > logging.INFO]) == 3
    assert len(dset[dset["levelno"] > logging.WARNING]) == 2
    assert len(dset[dset["levelno"] > logging.ERROR]) == 1
    assert len(dset[dset["levelno"] > logging.CRITICAL]) == 0
    assert np.array_equal(dset.dtype.names, attributes)

    dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_is_logging_dataset() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    _ = root.create_dataset("/a/b/regular")
    _ = root.create_dataset_logging("log")
    _ = root.create_dataset("regular")
    _ = root.create_dataset_logging("/a/b/log")
    _ = root.create_dataset_logging("/a/b/log2")

    log_datasets = [dset for dset in root.datasets() if root.is_dataset_logging(dset)]

    assert len(list(root.items())) == 7
    assert len(list(root.descendants())) == 2
    assert len(list(root.datasets())) == 5
    assert len(log_datasets) == 3

    assert len(logging.getLogger().handlers) == num_initial_handlers + 3

    for dset in root.datasets():
        if root.is_dataset_logging(dset):
            dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_invalid_attributes() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    # cannot be an empty list/tuple
    with pytest.raises(ValueError, match=r"Must specify logging attributes"):
        _ = root.create_dataset_logging("log", attributes=[])
    with pytest.raises(ValueError, match=r"Must specify logging attributes"):
        _ = root.create_dataset_logging("log", attributes=())

    # every element must be a string
    with pytest.raises(ValueError, match=r"as strings"):
        _ = root.create_dataset_logging("log", attributes=[1, 2, 3])  # type: ignore[list-item]  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match=r"as strings"):
        _ = root.create_dataset_logging("log", attributes=["1", "2", 3])  # type: ignore[list-item]  # pyright: ignore[reportArgumentType]

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_initial_shape() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()

    num_records = 1234

    log1 = root.create_dataset_logging("log1", shape=(10000,))
    log2 = root.create_dataset_logging("log2")
    log3 = root.create_dataset_logging("log3", size=256)
    log4 = root.create_dataset_logging("log4", size=0)

    # the shape is an argument of Dataset and does not get passed to the Metadata
    assert "shape" not in log1.metadata

    # specifying the `size` gets popped from the kwarg and gets converted to a `shape` kwarg
    assert "size" not in log3.metadata
    assert "shape" not in log3.metadata

    assert len(logging.getLogger().handlers) == num_initial_handlers + 4

    assert len(log1) == 10000
    assert len(log2) == 0
    assert len(log3) == 256
    assert len(log4) == 0

    for i in range(num_records):
        logging.info(i)  # just to be different, use the root logger  # noqa: LOG015

    assert len(log1) == 10000
    assert len(log2) == num_records
    assert len(log3) == 1380
    assert len(log4) == 1267

    for dset in root.datasets():
        assert isinstance(dset, DatasetLogging)
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
        assert isinstance(dset, DatasetLogging)
        dset.remove_handler()

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_initial_index_value() -> None:  # noqa: PLR0915
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter(file=Path(tempfile.gettempdir()) / "msl-io-junk.json")
    _ = root.create_dataset_logging("log")

    n = 10

    for i in range(n):
        logger.info("message %d", i)

    assert len(root.log) == n

    root.write(mode="w")

    assert isinstance(root.file, Path)
    root2 = read(root.file)
    root3 = read(root.file)

    # specify more than n elements
    _ = root2.require_dataset_logging(root.log.name, size=n + 5)

    # specify less than n elements which automatically gets increased to n
    # also specify shape as an integer which gets cast to a 1-d tuple
    _ = root3.require_dataset_logging(root.log.name, shape=n - 5)

    assert len(logging.getLogger().handlers) == num_initial_handlers + 3

    root.file.unlink()

    assert root2.log.size == n + 5
    assert root3.log.size == n  # gets increased to n

    assert isinstance(root.log, DatasetLogging)
    root.log.remove_handler()
    for i in range(n, 2 * n):
        logger.info("message %d", i)

    assert root.log.size == n
    assert root2.log.size == 24
    assert root3.log.size == 27

    root.log.remove_empty_rows()
    assert isinstance(root2.log, DatasetLogging)
    root2.log.remove_empty_rows()
    assert isinstance(root3.log, DatasetLogging)
    root3.log.remove_empty_rows()

    assert root.log.size == n
    assert root2.log.size == 2 * n
    assert root3.log.size == 2 * n

    root2.log.remove_handler()
    for i in range(2 * n, 3 * n):
        logger.info("message %d", i)

    assert root.log.size == n
    assert root2.log.size == 2 * n
    assert root3.log.size == 39

    root.log.remove_empty_rows()
    root2.log.remove_empty_rows()
    root3.log.remove_empty_rows()

    assert root.log.size == n
    assert root2.log.size == 2 * n
    assert root3.log.size == 3 * n

    messages1 = root["log"]["message"]
    messages2 = root2["log"]["message"]
    messages3 = root3["log"]["message"]
    for i in range(3 * n):
        if i < n:
            assert messages1[i] == f"message {i}"  # type: ignore[index]  # pyright: ignore[reportArgumentType]
        if i < 2 * n:
            assert messages2[i] == f"message {i}"  # type: ignore[index]  # pyright: ignore[reportArgumentType]
        assert messages3[i] == f"message {i}"  # type: ignore[index]  # pyright: ignore[reportArgumentType]

    root3["log"].remove_handler()  # type: ignore[operator]  # pyright: ignore[reportCallIssue]

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_invalid_shape_or_size() -> None:
    root = JSONWriter()

    with pytest.raises(ValueError, match=r"Invalid shape"):
        _ = root.create_dataset_logging("log", shape=())

    with pytest.raises(ValueError, match=r"Invalid shape"):
        _ = root.create_dataset_logging("log", shape=[])

    with pytest.raises(ValueError, match=r"Invalid shape"):
        _ = root.create_dataset_logging("log", shape=(10, 5))

    with pytest.raises(ValueError, match=r"Invalid shape"):
        _ = root.create_dataset_logging("log", shape=(-1,))

    with pytest.raises(ValueError, match=r"Invalid shape"):
        _ = root.create_dataset_logging("log", size=-1)

    assert len(logging.getLogger().handlers) == num_initial_handlers


def test_set_logger() -> None:
    assert len(logging.getLogger().handlers) == num_initial_handlers

    root = JSONWriter()
    _ = root.create_dataset_logging("log")

    assert isinstance(root.log, DatasetLogging)

    for obj in [None, "no", JSONWriter, logging.INFO, logging.Formatter, logging.Handler]:
        with pytest.raises(AttributeError, match=r"no attribute 'level'"):
            root.log.set_logger(obj)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

    root.log.set_logger(logger)
    root.log.remove_handler()
    assert len(logging.getLogger().handlers) == num_initial_handlers
