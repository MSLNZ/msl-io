"""
A :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.
"""
import logging

import numpy as np

from .dataset import Dataset


class DatasetLogging(Dataset, logging.Handler):

    def __init__(self, name, parent, level=logging.NOTSET, attributes=None, **metadata):
        """A :class:`~msl.io.dataset.Dataset` that handles :mod:`logging` records.

        Do not instantiate directly. Create a new :class:`DatasetLogging` using
        :meth:`~msl.io.group.Group.create_dataset_logging`.

        Parameters
        ----------
        name : :class:`str`
            A name to associate with the :class:`~msl.io.dataset.Dataset`.
        parent : :class:`~msl.io.group.Group`
            The parent :class:`~msl.io.group.Group` to the :class:`~msl.io.dataset.Dataset`.
        level : :class:`int` or :class:`str`
            The :ref:`logging level <levels>` to use.
        attributes : :class:`list` of :class:`str`
            A list of :ref:`attribute names <logrecord-attributes>` to include in the
            :class:`~msl.io.dataset.Dataset` for each :ref:`logging record <log-record>`.
        **metadata
            All other key-value pairs will be used as
            :class:`~msl.io.metadata.Metadata` for the :class:`~msl.io.dataset.Dataset`.
        """
        self._attributes = attributes

        root = logging.getLogger()
        if len(root.handlers) == 0:
            fmt = ' '.join('%({})s'.format(a) for a in attributes)
            logging.basicConfig(level=level, format=fmt)

        # these keys in the metadata are used to distinguish a DatasetLogging
        # object from a regular Dataset
        if isinstance(level, str):
            level = getattr(logging, level)
        metadata['logging_level'] = level
        metadata['logging_level_name'] = logging.getLevelName(level)
        self._dtype = np.dtype([(a, np.object) for a in attributes])

        # call Dataset.__init__ before Handler.__init__ in case the Dataset cannot be created
        Dataset.__init__(self, name, parent, False, dtype=self._dtype, **metadata)

        # the Handler will overwrite the self._name attribute so we create a reference to the
        # `name` of the Dataset and then set the `name` of the Handler after it is initialized
        name = self._name
        logging.Handler.__init__(self, level=level)
        self.set_name(name)

        root.addHandler(self)

    def __eq__(self, other):
        # Must override __eq__ because  calling root.addHandler(self) in
        # DatasetLogging.__init__ checks for the following condition:
        #   "if not (hdlr in self.handlers):"
        # and this could fail if adding multiple DatasetLogging instances
        # to the RootLogger and the Dataset's are emtpy. Every DatasetLogging
        # instance must be unique because every Vertex is unique so this
        # method can simply return False.
        return False

    def remove_handler(self):
        """Remove this :class:`~logging.Handler` from the ``RootLogger``.

        After calling this method :ref:`logging records <log-record>` are no longer
        appended to the :class:`~msl.io.dataset.Dataset`.
        """
        logging.getLogger().removeHandler(self)

    def emit(self, record):
        latest = tuple(record.__dict__[a] for a in self._attributes)
        row = np.asarray(latest, dtype=self._dtype)
        self._data = np.append(self._data, row)
