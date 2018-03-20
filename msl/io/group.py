from .metadata import Metadata


class Group(object):

    def __init__(self, name, metadata, parent=None):
        self._name = name
        self._parent = parent
        self._datasets = {}
        self._subgroups = {}
        self._metadata = Metadata(**metadata)

    @property
    def metadata(self):
        return self._metadata

    def add_metadata(self, metadata):
        self._metadata.update(metadata)

    def add_subgroup(self, name, metadata):
        group = Group(name, metadata, self)
        self._subgroups[name] = group

    def add_dataset(self, name, dataset):
        self._datasets[name] = dataset
