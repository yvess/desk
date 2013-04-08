# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals

import os
import sys
sys.path.append("../")
import unittest
from couchdbkit import Server
from desk.utils import CouchdbUploader
import time
import json
from copy import copy

from desk.plugin.base import MergedDoc, VersionDoc
from desk.plugin.dns.dnsbase import DnsValidator
from desk.plugin.dns.powerdns import Powerdns
from desk.utils import ObjectDict
from desk.worker import Worker


class WorkerTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "couchdb_uri": "http://localhost:5984",
            "couchdb_db": "desk_tester",
        }
        self.conf = {
            "powerdns_backend": "sqlite",
            "powerdns_db": "/etc/powerdns/dns.db",
        }
        self.conf.update(self.settings)
        s = Server()
        self.s = s
        s.create_db(self.settings['couchdb_db'])
        self.db = self.s.get_db(self.settings["couchdb_db"])
        self.up = CouchdbUploader(path=os.path.dirname(__file__), **self.settings)
        status_code = self.up.put(
            data="@fixtures/couchdb-design.json",
            doc_id="_design/{couchdb_db}"
        )
        if not status_code == 201:
            s.delete_db(self.settings["couchdb_db"])
            #raise Exception("Error with couchdb test database, http code:{}".format(status_code))

        worker_id = "worker-localhost"
        d = {
           "_id": worker_id, "type": "worker", "hostname": "localhost",
           "provides": {
               "dns": [{"backend": "powerdns"}]
           }
        }
        self.assertTrue(self.up.put(data=json.dumps(d), doc_id=worker_id) == 201)
        self.assertTrue(self.up.put(data="@fixtures/couchdb-template-dns.json", doc_id="template-email") == 201)
        self.assertTrue(self.up.put(data="@fixtures/couchdb-map-ips.json", doc_id="map-ips") == 201)

    def tearDown(self):
        has_domain = Powerdns(ObjectDict(**self.conf)).check_domain("test.tt")
        if has_domain:
            self._remove_domain("test.tt")
        self.s.delete_db(self.settings["couchdb_db"])

    def _add_domain_test_tt(self, run=True):
        dns_id = "dns-test.tt"
        self.assertTrue(self.up.put(data="@fixtures/couchdb-dns-test.tt.json", doc_id=dns_id) == 201)
        queue_id = self._create_queue_doc()
        if run:
            self._run_worker()
        return (dns_id, queue_id)

    def _remove_domain(self, domain, docs=None):
        # cleanup
        pdns = Powerdns(ObjectDict(**self.conf))
        pdns.del_domain(domain)
        if docs:
            self.db.delete_doc(docs)

    def _run_worker(self):
        w = Worker(self.conf, hostname="localhost")
        w.once()

    def _get_dns_validator(self, doc_id, lookup={'ns1.test.tt': "127.0.0.1", 'ns2.test.tt': "127.0.0.1"}):
        doc = MergedDoc(self.db, self.db.get(doc_id)).doc
        validator = DnsValidator(doc, lookup=lookup)
        return validator

    def _create_queue_doc(self):
        current_time = time.localtime()
        queue_id = "queue-{}".format(self.s.next_uuid())
        queue_doc = {
            "_id": queue_id,
            "date": time.strftime("%Y-%m-%d %H:%M:%S %z", current_time),
            "type": "queue", "sender": "pad", "state": "new"
        }
        self.assertTrue(self.up.put(data=json.dumps(queue_doc), doc_id=queue_id) == 201)
        return queue_id

    def test_worker_settings(self):
        doc = self.db.get("worker-localhost")
        self.assertTrue(doc['provides']['dns'][0]["backend"] == "powerdns")

    def test_new_domain(self):
        dns_id, queue_id = self._add_domain_test_tt()
        self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, queue_id])

    def test_update_record(self):
        dns_id, queue_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        dns_doc['a'][4]['ip'] = "1.1.1.21"
        dns_doc['a'][1]['host'] = "ns3"
        dns_doc['cname'][0]['host'] = "ns1"
        VersionDoc(self.db, dns_doc).create_version()
        queue_id = self._create_queue_doc()
        self._run_worker()
        self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, queue_id])

    def test_complete_change_record(self):
        dns_id, queue_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        changed_a = copy(dns_doc['a'][4])
        dns_doc['a'][4]['ip'] = "1.1.1.21"
        dns_doc['a'][4]['host'] = "www2"
        VersionDoc(self.db, dns_doc).create_version()
        queue_id = self._create_queue_doc()
        self._run_worker()
        self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        self.assertFalse(self._get_dns_validator('dns-test.tt').check_one_record('A', 'ip', q_key='host', item=changed_a))
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, queue_id])

    def test_append_record(self):
        dns_id, queue_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        dns_doc['a'].append({'host': "forum", 'ip': "1.1.1.25"})
        dns_doc['cname'].append({'alias': "super", 'host': "www"})
        VersionDoc(self.db, dns_doc).create_version()
        queue_id = self._create_queue_doc()
        self._run_worker()
        self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, queue_id])

    def test_delete_record(self):
        dns_id, queue_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        removed_a = dns_doc['a'].pop(4)
        VersionDoc(self.db, dns_doc).create_version()
        queue_id = self._create_queue_doc()
        self._run_worker()
        self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        self.assertFalse(self._get_dns_validator('dns-test.tt').check_one_record('A', 'ip', q_key='host', item=removed_a))
        self._remove_domain('test.tt', docs=[dns_id, queue_id])

if __name__ == '__main__':
    unittest.main()
