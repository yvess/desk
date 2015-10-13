# coding: utf-8
from __future__ import absolute_import, print_function
from __future__ import division, unicode_literals
from ldif import LDIFParser
import hashlib
from couchdbkit import Server
from desk.command import DocsProcessor


class IspmanDnsLDIF(LDIFParser):
    def __init__(self, input, output, settings, clients_ldif=None, editor=None):
        LDIFParser.__init__(self, input)
        self.domains = {}
        self.domains_lookup = (
            clients_ldif.domains_lookup if clients_ldif else None
        )
        self.editor = editor
        self.a_record_ips = set([])
        self.a_record_hosts = {}
        self.server = Server(settings.couchdb_uri)
        self.db = self.server.get_db(settings.couchdb_db)

    def handle(self, dn, entry):
        if dn.startswith('relativeDomainName='):
            domain = ".".join(
                [dc.split('=')[1] for dc in dn.split(',')
                 if dc.startswith('dc=')]
            )
            domain = domain.decode("utf-8").encode("iso8859-1")
            if domain not in self.domains:
                self.add_domain(domain)

            def cname(entry):
                self.domains[domain]['cname'].append(
                    {'alias': entry['relativeDomainName'][0].strip(),
                     'host': entry['cNAMERecord'][0].strip()}
                )

            def a(entry):
                host = entry['relativeDomainName'][0].strip()
                ip = entry['aRecord'][0].strip()
                self.domains[domain]['a'].append(
                    {'host': host,
                     'ip': ip}
                )
                self.a_record_ips.add(ip)
                full_host = "%s.%s" % (host, domain)
                if ip in self.a_record_hosts:
                    self.a_record_hosts[ip].append(full_host)
                else:
                    self.a_record_hosts[ip] = [full_host]

            def mx(entry):
                entry = entry['mXRecord'][0].split(' ')
                self.domains[domain]['mx'].append(
                    {'host': entry[1].strip(),
                     'priority': entry[0]}
                )

            def ns(entry):
                nameserver = entry['nSRecord'][0]
                self.domains[domain]['nameservers'].append(nameserver)
                self.domains[domain]['nameservers'].sort()

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
            next_uuid = self.server.next_uuid()
            self.domains[domain] = {
                '_id': 'domain-%s' % next_uuid,
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
            # for strange umlaut bug
            client = client.decode("utf-8").encode("iso8859-1")
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


class DnsDocsProcessor(DocsProcessor):
    allowed_template_type = 'dns'
    map_id = 'map-ips'
    replace_id = 'replace-cnames'

    def postprocess_tpl(self, doc):
        [doc.pop(key) for key in doc.keys() if key.startswith('soa_')]
        return doc

    def postprocess_doc(self, doc):
        reverse_map_dict = {v: k for k, v in self.map_dict.iteritems()}
        if 'a' in doc:
            for a_record in doc['a']:
                if a_record['ip'] in reverse_map_dict:
                    a_record['ip'] = reverse_map_dict[a_record['ip']]
        if 'cname' in doc:
            for cname in doc['cname']:
                if cname['host'] in self.replace_dict:
                    cname['host'] = self.replace_dict[cname['host']]
        return doc
