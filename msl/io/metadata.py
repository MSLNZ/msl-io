from collections import MutableMapping, KeysView, ItemsView, ValuesView


class Metadata(MutableMapping):

    def __init__(self, **kwargs):
        self.__dict__['_mapping'] = dict(**kwargs)

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __delitem__(self, item):
        del self._mapping[item]

    def __getattr__(self, item):
        return self._mapping[item]

    def __setattr__(self, item, value):
        self._mapping[item] = value

    def __getitem__(self, item):
        return self._mapping[item]

    def __setitem__(self, item, value):
        if item in self._mapping:
            print('warning ' + item)
        self._mapping[item] = value

    def clear(self):
        raise ValueError('Cannot clear the metadata')

    def keys(self):
        # Return a view for Python 2
        return KeysView(self)

    def values(self):
        # Return a view for Python 2
        return ValuesView(self)

    def items(self):
        # Return a view for Python 2
        return ItemsView(self)
