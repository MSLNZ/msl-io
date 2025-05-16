"""
A :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.
"""
import logging
from datetime import datetime

import numpy as np

from .dataset import Dataset


class DatasetLogging(Dataset, logging.Handler):

    def __init__(self, name, parent, level=logging.NOTSET, attributes=None, logger=None, date_fmt=None, **kwargs):
        """A :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.

        Do not instantiate directly. Create a new :class:`DatasetLogging` using
        :meth:`~msl.io.group.Group.create_dataset_logging`.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        parent : :class:`~msl.io.group.Group`
            The parent :class:`~msl.io.group.Group` to the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`, optional
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` or :class:`tuple` of :class:`str`, optional
            The :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
        logger : :class:`~logging.Logger`, optional
            The :class:`~logging.Logger` that this :class:`DatasetLogging` object
            will be added to. If :data:`None` then it is added to the ``root`` :class:`~logging.Logger`.
        date_fmt : :class:`str`, optional
            The :class:`~datetime.datetime` :ref:`format code <strftime-strptime-behavior>`
            to use to represent the ``asctime`` :ref:`attribute <logrecord-attributes>` in.
        **kwargs
            Additional keyword arguments are passed to :class:`~msl.io.dataset.Dataset`.
            The default behaviour is to append every :ref:`logging record <log-record>`
            to the :class:`~msl.io.dataset.Dataset`. This guarantees that the size of the
            :class:`~msl.io.dataset.Dataset` is equal to the number of
            :ref:`logging records <log-record>` that were added to it. However, this behaviour
            can decrease the performance if many :ref:`logging records <log-record>` are
            added often because a copy of the data in the :class:`~msl.io.dataset.Dataset` is
            created for each :ref:`logging record <log-record>` that is added. You can improve
            the performance by specifying an initial size of the :class:`~msl.io.dataset.Dataset`
            by including a `shape` or a `size` keyword argument. This will also automatically
            create additional empty rows in the :class:`~msl.io.dataset.Dataset`, that is
            proportional to the size of the :class:`~msl.io.dataset.Dataset`, if the size of the
            :class:`~msl.io.dataset.Dataset` needs to be increased. If you do this then you will
            want to call :meth:`.remove_empty_rows` before writing :class:`DatasetLogging` to a
            file or interacting with the data in :class:`DatasetLogging` to remove the extra
            rows that were created.
        """
        if not attributes or not all(isinstance(a, str) for a in attributes):
            raise ValueError(f"Must specify attribute names as strings, got: {attributes}")

        self._logger = None
        self._attributes = tuple(attributes)
        self._uses_asctime = "asctime" in attributes
        self._date_fmt = date_fmt

        if isinstance(level, str):
            level = getattr(logging, level)

        # these 3 keys in the metadata are used to distinguish a DatasetLogging
        # object from a regular Dataset object
        kwargs["logging_level"] = level
        kwargs["logging_level_name"] = logging.getLevelName(level)
        kwargs["logging_date_format"] = date_fmt
        self._dtype = np.dtype([(a, object) for a in attributes])

        self._auto_resize = "size" in kwargs or "shape" in kwargs
        if self._auto_resize:
            if "size" in kwargs:
                kwargs["shape"] = (kwargs.pop("size"),)
            elif isinstance(kwargs["shape"], int):
                kwargs["shape"] = (kwargs["shape"],)

            shape = kwargs["shape"]
            if len(shape) != 1:
                raise ValueError(f"Invalid shape {shape}, the number of dimensions must be 1")
            if shape[0] < 0:
                raise ValueError(f"Invalid shape {shape}")

        # call Dataset.__init__ before Handler.__init__ in case the Dataset cannot be created
        Dataset.__init__(self, name, parent, False, dtype=self._dtype, **kwargs)

        self._index = np.count_nonzero(self._data)
        if self._auto_resize and self._data.shape < kwargs["shape"]:
            self._resize(new_allocated=kwargs["shape"][0])

        # the Handler will overwrite the self._name attribute, so we create a reference to the
        # `name` of the Dataset and then set the `name` of the Handler after it is initialized
        name = self._name
        logging.Handler.__init__(self, level=level)
        self.set_name(name)

        self.set_logger(logger or logging.getLogger())

    def __eq__(self, other):
        # Must override __eq__ because  calling root.addHandler(self) in
        # DatasetLogging.__init__ checks for the following condition:
        #   "if not (hdlr in self.handlers):"
        # and this could fail if adding multiple DatasetLogging instances
        # to the RootLogger and the Datasets are emtpy. Every DatasetLogging
        # instance must be unique because every Vertex is unique so this
        # method can simply return False.
        return False

    def __hash__(self):
        # need to override for linux and macOS running Python 3.7+
        return logging.Handler.__hash__(self)

    @property
    def attributes(self):
        """:class:`tuple` of :class:`str`: The :ref:`attribute names <logrecord-attributes>`
        used by the :class:`DatasetLogging` object.
        """
        return self._attributes

    @property
    def date_fmt(self):
        """:class:`str`: The :class:`~datetime.datetime` :ref:`format code <strftime-strptime-behavior>`
        that is used to represent the ``asctime`` :ref:`attribute <logrecord-attributes>` in.
        """
        return self._date_fmt

    @property
    def logger(self):
        """:class:`~logging.Logger`: The :class:`~logging.Logger` that this
        :class:`DatasetLogging` object is added to.
        """
        return self._logger

    def remove_empty_rows(self):
        """Remove empty rows from the :class:`~msl.io.dataset.Dataset`.

        If the :class:`DatasetLogging` object was initialized with a `shape` or a `size` keyword
        argument then the size of the :class:`~msl.io.dataset.Dataset` is always :math:`\\geq`
        to the number of :ref:`logging records <log-record>` that were added to it. Calling this
        method will remove the rows in the :class:`~msl.io.dataset.Dataset` that were not
        from a :ref:`logging record <log-record>`.
        """
        # don't use "is not None" since this does not work as expected
        self._data = self._data[self._data[self._dtype.names[0]] != None]

    def remove_handler(self):
        """Remove this class's :class:`~logging.Handler` from the associated :class:`~logging.Logger`.

        After calling this method :ref:`logging records <log-record>` are no longer
        added to the :class:`~msl.io.dataset.Dataset`.
        """
        if self._logger is not None:
            self._logger.removeHandler(self)

    def set_logger(self, logger):
        """Add this class's :class:`~logging.Handler` to a :class:`~logging.Logger`.

        Parameters
        ----------
        logger : :class:`~logging.Logger`
            The :class:`~logging.Logger` to add this class's :class:`~logging.Handler` to.
        """
        if not isinstance(logger, logging.Logger):
            raise TypeError("Must be a logging.Logger object")

        level = self.metadata.logging_level
        if logger.level == 0 or logger.level > level:
            logger.setLevel(level)

        self.remove_handler()
        logger.addHandler(self)
        self._logger = logger

    def emit(self, record):
        """Overrides the :meth:`~logging.Handler.emit` method."""
        record.message = record.getMessage()
        if self._uses_asctime:
            record.asctime = datetime.fromtimestamp(record.created).strftime(self._date_fmt)
        latest = tuple(record.__dict__[a] for a in self._attributes)
        row = np.asarray(latest, dtype=self._dtype)
        if self._auto_resize:
            if self._index >= self._data.size:
                self._resize()
            self._data[self._index] = row
            self._index += 1
        else:
            self._data = np.append(self._data, row)

    def _resize(self, new_allocated=None):
        # Over-allocates proportional to the size of the ndarray, making room
        # for additional growth. This follows the over-allocating procedure that
        # Python uses when appending to a list object, see `list_resize` in
        # https://github.com/python/cpython/blob/master/Objects/listobject.c
        if new_allocated is None:
            new_size = self._data.size + 1
            new_allocated = new_size + (new_size >> 3) + (3 if new_size < 9 else 6)

        # don't use self._data.resize() because that fills the newly-created rows
        # with 0 and want to fill the new rows with None to be explicit that the
        # new rows are not associated with logging records
        array = np.empty((new_allocated,), dtype=self._dtype)
        array[:self._data.size] = self._data
        self._data = array
