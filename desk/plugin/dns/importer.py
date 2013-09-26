# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from ldif import LDIFParser


class JsonImporter(object):
    def add_domain(self, domain):
        if domain not in self.domains:
            self.domains[domain] = {
                '_id': 'domain-{}'.format(domain),
                'state': 'new',
                'type': 'domain',
                'editor': 'import',
                'domain': domain,
                'client_id': "",
                'a': [],
                'cname': [],
                'mx': [],
                'nameservers': [],
            }


class IspmanDnsLDIF(LDIFParser, JsonImporter):
    def __init__(self, input, output):
        LDIFParser.__init__(self, input)
        self.domains = {}

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
