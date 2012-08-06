# coding: utf-8
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function


import abc


class DnsBase(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, doc):
        self.doc = doc

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""
        return
