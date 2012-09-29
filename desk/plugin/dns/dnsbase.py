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

    @abc.abstractmethod
    def add_domain(self, domain):
        """add new domain"""

    @abc.abstractmethod
    def del_domain(self, domain):
        """del domain"""

    @abc.abstractmethod
    def add_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        """add record"""

    @abc.abstractmethod
    def update_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        """update record"""

    @abc.abstractmethod
    def del_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        """delete record"""

    def set_doc(self, doc):
        """sets the doc to use"""
        self.doc = doc

    def set_diff(self, diff):
        """sets the json diff to use"""
        self.diff = diff
