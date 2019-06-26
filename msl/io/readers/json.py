"""
Reads a file that was created by :class:`~msl.io.writers.json.JSONWriter`.
"""
import json

import numpy as np

from msl.io import register, Reader


@register
class JSONReader(Reader):
    """Reads a file that was created by :class:`~msl.io.writers.json.JSONWriter`.

    version=1.0 specifications

        * A :class:`~msl.io.dataset.Dataset` uses a 'dtype' and a 'data' key to
          uniquely identify the JSON object as a :class:`~msl.io.dataset.Dataset`

        * If a metadata value is itself a :class:`dict` then it becomes a
          :class:`~msl.io.group.Group`
    """

    @staticmethod
    def can_read(url):
        return 'MSL JSONWriter' in Reader.get_lines(url, 1)[0]

    def read(self):
        with open(self.url, 'r') as fp:
            next(fp)  # skip the first line
            dict_ = json.load(fp)

        def is_dataset(obj):
            return ('dtype' in obj) and ('data' in obj)

        def create_dataset(parent, name, dataset):
            data, kwargs = None, dict()

            for sub_key, sub_value in dataset.items():
                if sub_key == 'data':
                    pass
                elif sub_key == 'dtype':
                    if isinstance(sub_value, str):
                        kwargs['data'] = np.asarray(dataset['data'], dtype=sub_value)
                    else:
                        kwargs['data'] = np.asarray(
                            [tuple(row) for row in dataset['data']],
                            dtype=[tuple(item) for item in sub_value]
                        )
                else:
                    kwargs.update(**{sub_key: sub_value})

            parent.create_dataset(name, **kwargs)

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

        return self
