"""
Read a file that was created by :class:`~msl.io.writers.json_.JSONWriter`.
"""
import json
import codecs

import numpy as np

from msl.io import (
    register,
    Reader,
)
from ..constants import IS_PYTHON2


@register
class JSONReader(Reader):

    @staticmethod
    def can_read(url, **kwargs):
        """Checks if the text ``MSL JSONWriter`` is in the first line of the file."""
        return 'MSL JSONWriter' in Reader.get_lines(url, 1, **kwargs)[0]

    def read(self, **kwargs):
        """Read the file that was created by :class:`~msl.io.writers.json_.JSONWriter`

        If a :class:`~msl.io.metadata.Metadata` `key` has a `value` that is a
        :class:`list` then the list is converted to an :class:`~numpy.ndarray`
        with :class:`~numpy.dtype` = :class:`object`

        Parameters
        ----------
        **kwargs
            Accepts `encoding` and `errors` keyword arguments which are passed to
            :func:`open`. The default `encoding` value is ``'utf-8'`` and the default
            `errors` value is ``'strict'``. All additional keyword arguments are passed to
            `json.loads <https://docs.python.org/3/library/json.html#json.loads>`_.
        """
        open_kwargs = {
            'encoding': kwargs.pop('encoding', 'utf-8'),
            'errors': kwargs.pop('errors', 'strict'),
        }

        if IS_PYTHON2:
            opener = codecs.open  # this allows the encoding and errors kwargs to be used
        else:
            opener = open

        with opener(self.url, mode='r', **open_kwargs) as fp:
            fp.readline()  # skip the first line
            dict_ = json.loads(fp.read(), **kwargs)

        def list_to_ndarray(list_):
            # convert a Metadata value to ndarray because one can easily make ndarray read only
            # use dtype=object because it guarantees that the data types are preserved
            # for example,
            #   >>> a = np.asarray([True, -5, 0.002345, 'something', 49.1871524])
            #   >>> a
            #   array(['True', '-5', '0.002345', 'something', '49.1871524'], dtype='<U32')
            # would cast every element to a string
            # also a regular Python list stores items as objects anyways
            return np.asarray(list_, dtype=object)

        def create_group(parent, name, vertex):
            group = self if parent is None else parent.create_group(name)
            for key, value in vertex.items():
                if not isinstance(value, dict):  # Metadata
                    if isinstance(value, list):
                        value = list_to_ndarray(value)
                    group.metadata[key] = value
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
                        else:  # Metadata
                            if isinstance(dval, list):
                                dval = list_to_ndarray(dval)
                            kws[dkey] = dval
                    group.create_dataset(key, **kws)
                else:  # use recursion to create a sub-Group
                    create_group(group, key, value)

        # create the root group
        create_group(None, '', dict_)
