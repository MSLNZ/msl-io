

class Reader(object):

    def __init__(self, url, **kwargs):
        self._url = url

    @property
    def url(self):
        return self._url

    @staticmethod
    def can_read(url):
        return False

    def read(self):
        raise NotImplementedError

    def create_root(self):
        return Root(self.url)


class Root(object):

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return self._url


class Group(object):

    def metadata(self):
        return Metadata()

    def dataset(self):
        return Dataset()


class Metadata(object):
    pass


class Dataset(object):
    pass
