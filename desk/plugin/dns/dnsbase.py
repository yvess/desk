# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import abc
from socket import gethostbyname
import dns.resolver


class DnsValidator(object):

    def __init__(self, doc, lookup=None):
        self.doc = doc
        self.domain = doc['domain']
        self.resolver = dns.resolver.Resolver()
        self.lookup = lookup
        self.valid = []

    def _validate(self, record_type, item_key, q_key='domain', answer_attr='address'):
        items = self.doc[record_type.lower()]
        for item in items:
            if q_key == 'domain':
                q = self.domain
            elif not item[q_key].endswith(".") and q_key in ('host', 'alias'):
                q = "{}.{}".format(item[q_key], self.domain)
            else:
                q = item[q_key]
            answers = []
            for answer in self.resolver.query(q, record_type):
                print(type(answer), dir(answer))
                answer_value = answer if hasattr(answer, '__getitem__') else getattr(answer, answer_attr)
                answer_value = unicode(answer_value)
                if answer_value.endswith("."):
                    answer_value = answer_value[:-1]
                answers.append(answer_value)
            item_value = unicode(item[item_key])
            self.valid.append(True if item_value in answers else False)

    def is_valid(self):
        for ns in self.doc['nameservers'].split(','):
            domain, ns = self.domain, ns.strip()
            self.resolver.nameservers = [gethostbyname(ns) if not self.lookup else self.lookup[ns]]
            self._validate('A', 'ip', q_key='host')
            self._validate('MX', 'host', answer_attr='exchange')
            self._validate('MX', 'priority', answer_attr='preference')
            self._validate('CNAME', 'host', q_key='alias', answer_attr='target')
        return all(self.valid)


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
