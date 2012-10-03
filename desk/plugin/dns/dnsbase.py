# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import abc
from desk.plugin.base import MergedDoc
from socket import gethostbyname
import dns.resolver


class DnsValidator(object):

    def __init__(self, db, doc):
        self.merged_doc = MergedDoc(db, doc).merged_doc
        self.db, self.doc = db, doc

    def validate(self, lookup=None):
        print("MergedDoc", self.merged_doc['nameservers'])
        for ns in self.merged_doc['nameservers'].split(','):
            domain, ns = self.merged_doc['domain'], ns.strip()
            # Set the DNS Server
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [gethostbyname(ns) if not lookup else lookup[ns]]
            for a in self.merged_doc['a']:
                print(a)
                answers = dns.resolver.query("{}.{}".format(a['host'], domain), 'A')
                for result in answers:
                    print(result)
            # self.record = self.r.req(name="www.yas.ch")
            #     print(record)
            #     if (record['name'], record['data']) == (a['host'], a['ip']):
            #         print(True)
            #     else:
            #         print(False)


class DnsBase(object):
    __metaclass__ = abc.ABCMeta
    validator = DnsValidator

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
