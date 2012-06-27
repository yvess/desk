import abc


class DnsBase(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, doc):
        self.doc = doc

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""
        return
