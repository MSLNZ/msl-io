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
            will be added to. If :data:`None` then adds it to the ``root`` :class:`~logging.Logger`.
        date_fmt : :class:`str`, optional
            The :class:`~datetime.datetime` :ref:`format code <strftime-strptime-behavior>`
            to use to represent the ``asctime`` :ref:`attribute <logrecord-attributes>` in.
        **kwargs
            Additional keyword arguments that are passed to :class:`~msl.io.dataset.Dataset`.
        """
        self._logger = None
        self._attributes = attributes
        self._uses_asctime = 'asctime' in attributes
        self._date_fmt = date_fmt

        if isinstance(level, str):
            level = getattr(logging, level)

        # these 3 keys in the metadata are used to distinguish a DatasetLogging
        # object from a regular Dataset object
        kwargs['logging_level'] = level
        kwargs['logging_level_name'] = logging.getLevelName(level)
        kwargs['logging_date_format'] = date_fmt
        self._dtype = np.dtype([(a, np.object) for a in attributes])

        # call Dataset.__init__ before Handler.__init__ in case the Dataset cannot be created
        Dataset.__init__(self, name, parent, False, dtype=self._dtype, **kwargs)

        # the Handler will overwrite the self._name attribute so we create a reference to the
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
        # to the RootLogger and the Dataset's are emtpy. Every DatasetLogging
        # instance must be unique because every Vertex is unique so this
        # method can simply return False.
        return False

    def __hash__(self):
        # need to override for linux and macOS running Python 3.7+
        return logging.Handler.__hash__(self)

    def remove_handler(self):
        """Remove this class's :class:`~logging.Handler` from the associated :class:`~logging.Logger`.

        After calling this method :ref:`logging records <log-record>` are no longer
        appended to the :class:`~msl.io.dataset.Dataset`.
        """
        if self._logger is not None:
            self._logger.removeHandler(self)

    def set_logger(self, logger):
        """Add this class's :class:`~logging.Handler` to a :class:`~logging.Logger`

        Parameters
        ----------
        logger : :class:`~logging.Logger`
            The :class:`~logging.Logger` to add this class's :class:`~logging.Handler` to.
        """
        if not isinstance(logger, logging.Logger):
            raise TypeError('Must be a logging.Logger object')

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
        self._data = np.append(self._data, row)
