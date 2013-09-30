# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from ldif import LDIFParser
import hashlib


class IspmanDnsLDIF(LDIFParser):

    def __init__(self, input, output, clients_ldif=None, editor=None):
        LDIFParser.__init__(self, input)
        self.domains = {}
        self.domains_lookup = (
            clients_ldif.domains_lookup if clients_ldif else None
        )
        self.editor = editor

    def handle(self, dn, entry):
        if dn.startswith('relativeDomainName='):
            domain = ".".join(
                [dc.split('=')[1] for dc in dn.split(',')
                 if dc.startswith('dc=')]
            )
            if domain not in self.domains:
                self.add_domain(domain)

            def cname(entry):
                self.domains[domain]['cname'].append(
                    {'alias': entry['relativeDomainName'][0],
                     'host': entry['cNAMERecord'][0]}
                )

            def a(entry):
                self.domains[domain]['a'].append(
                    {'host': entry['relativeDomainName'][0],
                     'ip': entry['aRecord'][0]}
                )

            def mx(entry):
                entry = entry['mXRecord'][0].split(' ')
                self.domains[domain]['mx'].append(
                    {'host': entry[1],
                     'priority': entry[0]}
                )

            def ns(entry):
                self.domains[domain]['nameservers'].append(
                    entry['nSRecord'][0]
                )

            if "cNAMERecord" in dn:
                cname(entry)
            elif "aRecord" in dn:
                a(entry)
            elif "mXRecord" in dn:
                mx(entry)
            elif "nSRecord" in dn:
                ns(entry)

    def add_domain(self, domain):
        if domain not in self.domains:
            self.domains[domain] = {
                '_id': 'domain-{}'.format(domain),
                'state': 'new',
                'type': 'domain',
                'domain': domain,
                'a': [],
                'cname': [],
                'mx': [],
                'nameservers': [],
            }
            if self.domains_lookup:
                self.domains[domain]['client_id'] = (
                    self.domains_lookup[domain]
                )
            if self.editor:
                self.domains[domain]['editor'] = self.editor


class IspmanClientLDIF(LDIFParser):

    def __init__(self, input, output, editor=None):
        LDIFParser.__init__(self, input)
        self.clients = {}
        self.domains_lookup = {}
        self.editor = editor

    def handle(self, dn, entry):
        if dn.startswith('ispmanDomain='):
            client = entry['ispmanDomainCustomer'][0]
            domain = entry['ispmanDomain'][0]
            if client not in self.clients:
                self.add_client(client)
            self.add_domain(domain, client)

    def _id_for_client(self, client):
        return 'client-{}'.format(hashlib.md5(client).hexdigest())

    def add_client(self, client):
        if client not in self.clients:
            _id = self._id_for_client(client)
            self.clients[_id] = {
                '_id': _id,
                'type': 'client',
                'editor': 'importer',
                'name': client,
            }
            if self.editor:
                self.clients['editor'] = self.editor

    def add_domain(self, domain, client):
        self.domains_lookup[domain] = self._id_for_client(client)
