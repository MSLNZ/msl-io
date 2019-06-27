"""
Writer for a JSON_ file format.

.. _JSON: https://www.json.org/
"""
import os
import json

import numpy as np

from .. import Writer
from ..metadata import Metadata
from ..base_io import Root


class JSONWriter(Writer):

    def write(self, url=None, root=None, **kwargs):
        """Write to a JSON_ file.

        The first line in the output file contains a description that the
        file was created by this :class:`JSONWriter`. It begins with a ``#`` and
        contains the version number of the :class:`JSONWriter`.

        Parameters
        ----------
        url : :class:`str`, optional
            The name of the file to write to. If :data:`None` then uses the value of
            `url` that was specified when :class:`JSONWriter` was created.
        root : :class:`~msl.io.base_io.Root`, optional
            Write `root` in JSON_ format. If :data:`None` the write the
            :class:`~msl.io.group.Group`\\s and :class:`~msl.io.dataset.Dataset`\\s
            in this :class:`JSONWriter`.
        **kwargs
            All key-value pairs are passed to
            `json.dump <https://docs.python.org/3/library/json.html#json.dump>`_.
            The default indentation is 2.
        """
        url = self.url if url is None else url
        if not url:
            raise ValueError('You must specify a url to write the file to')

        if root is None:
            root = self
        elif not isinstance(root, Root):
            raise TypeError('the root parameter must be a Root object')

        def add_dataset(d, dataset):
            if dataset.dtype.fields:
                # can't use dataset.dtype.fields.items() since Python < 3.6
                # does not preserve order in a dict
                d['dtype'] = [[n, str(dataset.dtype.fields[n][0])] for n in dataset.dtype.names]
            else:
                d['dtype'] = dataset.dtype.str
            d['data'] = dataset.tolist()

        def metadata_to_dict(metadata):
            d = dict()
            for k, v in metadata.items():
                if isinstance(v, Metadata):
                    d[k] = metadata_to_dict(v)
                elif isinstance(v, np.ndarray):
                    d[k] = v.tolist()
                elif isinstance(v, np.integer):
                    d[k] = int(v)
                elif isinstance(v, np.floating):
                    d[k] = float(v)
                elif isinstance(v, (complex, np.complexfloating)):
                    d[k] = str(v)
                else:
                    d[k] = v
            return d

        dict_ = dict(**metadata_to_dict(root.metadata))

        for name, value in root.items():
            vertices = name.split('/')
            root_key = vertices[1]

            if root_key not in dict_:
                dict_[root_key] = dict(**metadata_to_dict(value.metadata))
                if root.is_dataset(value):
                    add_dataset(dict_[root_key], value)

            if len(vertices)>2:
                vertex = dict_[root_key]
                for key in vertices[2:-1]:
                    vertex = vertex[key]

                leaf_key = vertices[-1]
                if leaf_key not in vertex:
                    vertex[leaf_key] = dict(**metadata_to_dict(value.metadata))
                    if root.is_dataset(value):
                        add_dataset(vertex[leaf_key], value)

        if 'indent' not in kwargs:
            kwargs['indent'] = 2

        mode = kwargs.pop('mode', None)
        # The 'x' mode was not introduced until Python 3.3
        # so we should check if the file already exists
        if not mode:
            if os.path.isfile(url):
                raise OSError('the {!r} file already exists'.format(url))
            mode = 'wt'

        print(dict_)
        with open(url, mode=mode) as fp:
            fp.write('#File created with: MSL {} version 1.0\n'.format(self.__class__.__name__))
            json.dump(dict_, fp, **kwargs)
