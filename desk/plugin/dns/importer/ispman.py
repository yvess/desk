# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from ldif import LDIFParser
from ..importer import JsonImporter


class IspmanLDIF(LDIFParser, JsonImporter):
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
                entry = entry['nSRecord'][0]
                nameservers = self.domains[domain]['nameservers']
                if not nameservers:
                    nameservers = entry
                else:
                    nameservers = "{}, {}".format(nameservers, entry)
                self.domains[domain]['nameservers'] = nameservers

            if "cNAMERecord" in dn:
                cname(entry)
            elif "aRecord" in dn:
                a(entry)
            elif "mXRecord" in dn:
                mx(entry)
            elif "nSRecord" in dn:
                ns(entry)


#parser = IspmanLDIF(open("ispmanDomain.ldif", 'rb'), sys.stdout)
#parser = IspmanLDIF(open("ou_DNS.ldif", 'rb'), sys.stdout)
#parser.parse()
