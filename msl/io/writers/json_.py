"""
Writer for a JSON_ file format. The corresponding :class:`~msl.io.base_io.Reader` is
:class:`~msl.io.readers.json_.JSONReader`.

.. _JSON: https://www.json.org/
"""
import os
import json
import codecs
from io import BufferedIOBase

import numpy as np

from .. import Writer
from ..metadata import Metadata
from ..base_io import Root
from ..constants import IS_PYTHON2

# Custom JSON encoder that writes a 1-dimensional list on a single line.
if IS_PYTHON2:
    from ._py2_json_encoder import _make_iterencode
else:
    from ._py3_json_encoder import _make_iterencode

_original_make_iterencode = json.encoder._make_iterencode


class JSONWriter(Writer):
    """Create a JSON_ writer."""

    def write(self, url=None, root=None, **kwargs):
        """Write to a JSON_ file.

        The first line in the output file contains a description that the
        file was created by the :class:`JSONWriter`. It begins with a ``#`` and
        contains a version number.

        Version 1.0 specifications

            * Use the ``'dtype'`` and ``'data'`` keys to uniquely identify a
              JSON_ object as a :class:`~msl.io.dataset.Dataset`.

            * If a :class:`~msl.io.metadata.Metadata` `key` has a `value` that is a
              :class:`~msl.io.metadata.Metadata` object then the `key` becomes the name
              of a :class:`~msl.io.group.Group` and the `value` becomes
              :class:`~msl.io.metadata.Metadata` of that :class:`~msl.io.group.Group`.

        Parameters
        ----------
        url : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The file to write the `root` to. If :data:`None` then uses the value of
            `url` that was specified when :class:`JSONWriter` was instantiated.
        root : :class:`~msl.io.base_io.Root`, optional
            Write `root` in JSON_ format. If :data:`None` then write the
            :class:`~msl.io.group.Group`\\s and :class:`~msl.io.dataset.Dataset`\\s
            in this :class:`JSONWriter`.
        **kwargs
            Accepts `mode`, `encoding` and `errors` keyword arguments which are passed
            to :func:`open`. The default `encoding` value is ``'utf-8'`` and the default
            `errors` value is ``'strict'``. All additional keyword arguments are passed to
            `json.dump <https://docs.python.org/3/library/json.html#json.dump>`_.
            The default indentation is 2.
        """
        if url is None:
            url = self.url
        if not url:
            raise ValueError('You must specify a url to write the file to')

        if root is None:
            root = self
        elif not isinstance(root, Root):
            raise TypeError('The root parameter must be a Root object')

        def add_dataset(d, dataset):
            if dataset.dtype.fields:
                # can't iterate over dataset.dtype.fields.items() since Python < 3.6
                # does not preserve order in a dict
                fields = dataset.dtype.fields
                d['dtype'] = [[n, str(fields[n][0])] for n in dataset.dtype.names]
            else:
                d['dtype'] = dataset.dtype.str
            d['data'] = dataset.tolist()

        def meta_to_dict(metadata):
            return dict((k, meta_to_dict(v) if isinstance(v, Metadata) else v)
                        for k, v in metadata.items())

        dict_ = dict(**meta_to_dict(root.metadata))

        for name, value in root.items():
            vertices = name.split('/')
            root_key = vertices[1]

            if root_key not in dict_:
                dict_[root_key] = dict(**meta_to_dict(value.metadata))
                if root.is_dataset(value):
                    add_dataset(dict_[root_key], value)

            if len(vertices) > 2:
                vertex = dict_[root_key]
                for key in vertices[2:-1]:
                    vertex = vertex[key]

                leaf_key = vertices[-1]
                if leaf_key not in vertex:
                    vertex[leaf_key] = dict(**meta_to_dict(value.metadata))
                    if root.is_dataset(value):
                        add_dataset(vertex[leaf_key], value)

        open_kwargs = {
            'mode': kwargs.pop('mode', None),
            'encoding': kwargs.pop('encoding', 'utf-8'),
            'errors': kwargs.pop('errors', 'strict')
        }

        if IS_PYTHON2:
            opener = codecs.open  # this allows the encoding and errors kwargs to be used
        else:
            # don't use codecs.open because the file looks better when opened in Notepad
            # (on Windows) when the standard open function use used
            opener = open

        is_file_like = hasattr(url, 'write')

        if not open_kwargs['mode']:
            open_kwargs['mode'] = 'w'
            if not is_file_like and os.path.isfile(url):
                raise IOError("A {!r} file already exists.\n"
                              "Specify mode='w' if you want to overwrite it.".format(url))

        if 'indent' not in kwargs:
            kwargs['indent'] = 2
        if 'cls' not in kwargs:
            kwargs['cls'] = _NumpyEncoder
            json.encoder._make_iterencode = _make_iterencode

        header = '#File created with: MSL {} version 1.0\n'.format(self.__class__.__name__)

        if is_file_like:
            if isinstance(url, BufferedIOBase):  # a bytes-like object is required
                encoding = open_kwargs['encoding']
                url.write(header.encode(encoding))
                url.write(json.dumps(dict_, **kwargs).encode(encoding))
            elif IS_PYTHON2:
                url.write(unicode(header))
                url.write(unicode(json.dumps(dict_, **kwargs)))
            else:
                url.write(header)
                json.dump(dict_, url, **kwargs)
        else:
            with opener(url, **open_kwargs) as fp:
                fp.write(header)
                json.dump(dict_, fp, **kwargs)

        if kwargs['cls'] is _NumpyEncoder:
            json.encoder._make_iterencode = _original_make_iterencode


class _NumpyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)

        # Let the base class raise the TypeError
        return json.JSONEncoder.default(self, obj)
