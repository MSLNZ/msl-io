from .group import Group


class Root(object):

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return self._url
