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

    def _setup_resolver(self, ns):
        self.resolver.nameservers = [
            gethostbyname(ns) if not self.lookup else self.lookup[ns]
        ]

    def _validate(self, record_type, item_key, q_key='domain',
                  answer_attr='address', return_check=False, items=None):
        if not items:
            items = self.doc[
                record_type.lower()
            ] if hasattr(self.doc, record_type.lower()) else []
        for item in items:
            if q_key == 'domain':
                q = self.domain
            # TODO do in host name calc in one place
            elif q_key in ('host', 'alias') and not item[q_key].endswith("."):
                if item[q_key] == "@":
                    q = self.domain  # special case for empty root domain
                else:
                    q = "{}.{}".format(item[q_key], self.domain)
            else:
                q = item[q_key]
            answers = []
            for answer in self.resolver.query(q, record_type):
                if hasattr(answer, '__getitem__'):
                    answer_value = answer
                else:
                    answer_value = getattr(answer, answer_attr)
                answer_value = unicode(answer_value)
                is_fqdn = False
                if answer_value.endswith("."):
                    is_fqdn = True
                answers.append(answer_value)
            item_value = unicode(item[item_key])
            if item_value.startswith('@ip_'):
                item_value = self.lookup_map[item_value]
            if is_fqdn and not item_value.endswith("."):
                if record_type == "MX":
                    item_value = "{}.".format(item_value)
                else:
                    # TODO do in host name calc in one place
                    item_value = "{}.{}.".format(item_value, self.domain)
            valid = True if item_value in answers else False
            if return_check:
                return valid
            else:
                self.valid.append(valid)

    def check_one_record(self, record_type, item_key,
                         q_key='domain', item=None):
        record_type = record_type.upper()
        lookup_answer_attr = {'CNAME': 'target', 'A': 'address'}
        answer_attr = lookup_answer_attr[record_type]
        for ns in self.doc['nameservers']:
            domain, ns = self.domain, ns
            self._setup_resolver(ns)
            try:
                self._validate(
                    record_type, item_key, q_key=q_key,
                    items=[item], answer_attr=answer_attr
                )
            except dns.resolver.NoAnswer:
                self.valid.append(False)
        is_valid = all(self.valid)
        self.valid = []
        return is_valid

    def do_check(self):
        for ns in self.doc['nameservers']:
            domain, ns = self.domain, ns
            self._setup_resolver(ns)
            self._validate('A', 'ip', q_key='host')
            self._validate('AAAA', 'ipv6', q_key='host')
            self._validate('MX', 'host', answer_attr='exchange')
            self._validate('MX', 'priority', answer_attr='preference')
            self._validate(
                'CNAME', 'host', q_key='alias', answer_attr='target'
            )
            self._validate('TXT', 'name')
        is_valid = all(self.valid)
        self.valid = []
        return is_valid


def dnsbase_structure_cname_value_trans(host, domain):
    if host.endswith("."):
        value = host[:-1]
    elif host == '@':
        value = domain
    else:
        value = ".".join([host, domain])
    return value


def to_fqdn(entry, domain=None):
    if entry.endswith('.'):
        return entry[:-1]
    if domain:
        return "%s.%s" % (entry, domain)
    return entry


def reverse_fqdn(domain, record):
    record, matched_domain, remainer = record.partition(".%s" % domain)
    if record == domain:
        return "@"
    if not matched_domain and not record.endswith('.'):
        record = "%s." % record
    if record == ".":
        return ""
    return record


def get_providers(doc):
    provider_key = 'nameservers'
    nameservers = [to_fqdn(provider) for provider in doc[provider_key]]
    return nameservers


class DnsBase(object):
    __metaclass__ = abc.ABCMeta
    validator = DnsValidator
    structure = [
        {
            'name': 'a',
            'key_id': 'host', 'value_id': 'ip',
            'key_trans': lambda host, domain: (
                ".".join([host, domain]) if host != "@" else domain
            )
        },
        {
            'name': 'aaaa',
            'key_id': 'host', 'value_id': 'ipv6',
            'key_trans': lambda host, domain: (
                ".".join([host, domain]) if host != "@" else domain
            )
        },
        {
            'name': 'cname',
            'key_id': 'alias', 'value_id': 'host',
            'key_trans': lambda alias, domain: (
                alias[:-1] if alias.endswith(".")
                else ".".join([alias, domain])
            ),
            'value_trans': dnsbase_structure_cname_value_trans
        },
        {
            'name': 'mx',
            'key_id': 'host', 'value_id': 'priority'
        },
        {
            'name': 'txt',
            'key_id': 'name', 'value_id': 'txt'
        },
        {
            'name': 'srv',
            'key_id': 'name', 'value_id': 'txt,priority'
        }
    ]
    map_doc_id = 'map-ips'

    @abc.abstractmethod
    def set_domain(self, domain, new):
        """Set the current domain."""

    @abc.abstractmethod
    def create(self):
        """Create the dns record."""

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""

    @abc.abstractmethod
    def delete(self, record):
        """delete the dns record."""

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

    @abc.abstractmethod
    def del_records(self, rtype, domain=None):
        """delete records from one rtype"""

    @abc.abstractmethod
    def get_domains(self):
        """get all domain names"""

    @abc.abstractmethod
    def get_records(self, domain=None):
        """get all records"""

    def set_docs(self, doc, prev_doc=None):
        """sets the doc to use"""
        self.doc = doc
        self.prev_doc = prev_doc

    def set_diff(self, diff):
        """sets the json diff to use"""
        self.diff = diff

    def set_lookup_map(self, doc):
        self.lookup_map = doc['map']
        self.validator.lookup_map = doc['map']

    def get_ttl(self, doc):
        if 'ttl' in doc:
            return doc['ttl']
        if 'soa_default_ttl' in doc:
            return doc['soa_default_ttl']
        return 86400
