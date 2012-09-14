# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import abc


class DnsBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create(self):
        """Create the dns record."""

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""

    def set_doc(self, doc):
        """sets the doc to use"""
        self.doc = doc
