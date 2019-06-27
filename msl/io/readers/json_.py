"""
Read a file that was created by :class:`~msl.io.writers.json.JSONWriter`.
"""
import json

import numpy as np

from msl.io import (
    register,
    Reader,
)
from ..metadata import Metadata


@register
class JSONReader(Reader):
    """
    Version 1.0 specifications

        * Use the ``'dtype'`` and ``'data'`` keys to uniquely identify a
          `JSON <https://www.json.org/>`_ object as a :class:`~msl.io.dataset.Dataset`.

        * If a :class:`~msl.io.metadata.Metadata` `key` has a `value` that is a
          :class:`~msl.io.metadata.Metadata` object then the `key` becomes the name
          of a :class:`~msl.io.group.Group` and the `value` becomes
          :class:`~msl.io.metadata.Metadata` of that :class:`~msl.io.group.Group`.

    """

    @staticmethod
    def can_read(url):
        """Checks if the text ``MSL JSONWriter`` is in the first line of the file."""
        return 'MSL JSONWriter' in Reader.get_lines(url, 1)[0]

    def read(self, **kwargs):
        """Read the file that was created by :class:`~msl.io.writers.json.JSONWriter`

        Parameters
        ----------
        **kwargs
            All key-value pairs are passed to
            `json.load <https://docs.python.org/3/library/json.html#json.load>`_.
        """
        with open(self.url, mode='rt') as fp:
            fp.readline()  # skip the first line
            dict_ = json.load(fp, **kwargs)

        def is_dataset(obj):
            return ('dtype' in obj) and ('data' in obj)

        def create_dataset(parent, name, dataset):
            kws = dict()
            for sub_key, sub_value in dataset.items():
                if sub_key == 'data':
                    pass
                elif sub_key == 'dtype':
                    if isinstance(sub_value, list):
                        kws['data'] = np.asarray(
                            [tuple(row) for row in dataset['data']],
                            dtype=[tuple(item) for item in sub_value]
                        )
                    else:
                        kws['data'] = np.asarray(dataset['data'], dtype=sub_value)
                else:
                    kws.update(**{sub_key: sub_value})
            parent.create_dataset(name, **kws)

        def create_group(parent, name, value):
            group = parent.create_group(name)
            for sub_key, sub_value in value.items():
                if not isinstance(sub_value, dict):
                    group.add_metadata(**{sub_key: sub_value})
                elif is_dataset(sub_value):
                    create_dataset(group, sub_key, sub_value)
                else:
                    create_group(group, sub_key, sub_value)
            return group

        for key, value in dict_.items():
            if not isinstance(value, dict):
                self.add_metadata(**{key: value})
            elif is_dataset(value):
                create_dataset(self, key, value)
            else:
                create_group(self, key, value)
