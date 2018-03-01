from .base import Reader

from . import register

@register.reader
class TXT(Reader):

    def __init__(self, url, **kwargs):
        Reader.__init__(self, url)

    @staticmethod
    def can_read(url):
        return Reader.extension(url) == '.txt'

    def read(self):
        return self.create_new_dataset()