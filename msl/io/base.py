import os

class Reader(object):

    def __init__(self, url, **kwargs):
        self._url = url

    @property
    def url(self):
        return self._url

    @classmethod
    def extension(cls, url):
        return os.path.splitext(url)[1]

    @staticmethod
    def can_read(url):
        return False

    def read(self):
        raise NotImplementedError

    def create_new_dataset(self):
        return Dataset()


class Dataset(object):
    pass