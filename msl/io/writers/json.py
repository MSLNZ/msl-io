import json

from .. import Writer
from ..metadata import Metadata


class JSONWriter(Writer):

    def save(self, *, url=None, root=None, indent=2, **kwargs):
        url = self.url if url is None else url

        def add_dataset(d, dataset):
            if dataset.dtype.fields:
                d['dtype'] = [[k, str(v[0])] for k, v in dataset.dtype.fields.items()]
            else:
                d['dtype'] = dataset.dtype.str
            d['data'] = dataset.tolist()

        def add_metadata(d, metadata):
            for k, v in metadata.items():
                if isinstance(v, Metadata):
                    d[k] = v._mapping
                else:
                    d[k] = v

        if root is None:
            root = self

        dict_ = dict()
        add_metadata(dict_, root.metadata)

        for name, value in root.items():
            vertices = name.split('/')
            root_key = vertices[1]

            if root_key not in dict_:
                dict_[root_key] = dict()
                add_metadata(dict_[root_key], value.metadata)
                if root.is_dataset(value):
                    add_dataset(dict_[root_key], value)

            if len(vertices)>2:
                vertex = dict_[root_key]
                for key in vertices[2:-1]:
                    vertex = vertex[key]

                leaf_key = vertices[-1]
                if leaf_key not in vertex:
                    vertex[leaf_key] = dict()
                    add_metadata(vertex[leaf_key], value.metadata)
                    if root.is_dataset(value):
                        add_dataset(vertex[leaf_key], value)

        kwargs['indent'] = indent

        with open(url, 'w') as fp:
            fp.write('#File created with: MSL {} version=1.0\n'.format(self.__class__.__name__))
            json.dump(dict_, fp, **kwargs)
