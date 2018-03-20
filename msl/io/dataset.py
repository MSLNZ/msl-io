from .metadata import Metadata


class Dataset(object):

    def __init__(self, name, metadata):
        self._name = name
        self._metadata = Metadata(**metadata)

    @property
    def metadata(self):
        return self._metadata
