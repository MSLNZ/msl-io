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
            `json.loads <https://docs.python.org/3/library/json.html#json.loads>`_.
        """
        with open(self.url, mode='rt') as fp:
            fp.readline()  # skip the first line
            dict_ = json.loads(fp.read(), **kwargs)

        def create_group(parent, name, vertex):
            group = self if parent is None else parent.create_group(name)
            for key, value in vertex.items():
                if not isinstance(value, dict):  # Metadata
                    group.add_metadata(**{key: value})
                elif 'dtype' in value and 'data' in value:  # Dataset
                    kws = dict()
                    for dkey, dval in value.items():
                        if dkey == 'data':
                            pass  # handled in the 'dtype' check
                        elif dkey == 'dtype':
                            if isinstance(dval, list):
                                kws['data'] = np.asarray(
                                    [tuple(row) for row in value['data']],
                                    dtype=[tuple(item) for item in dval])
                            else:
                                kws['data'] = np.asarray(value['data'], dtype=dval)
                        else:
                            kws[dkey] = dval
                    group.create_dataset(key, **kws)
                else:  # use recursion to create a Group
                    create_group(group, key, value)

        # create the root group
        create_group(None, '', dict_)