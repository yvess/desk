# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals


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
                'nameservers': "",
            }
