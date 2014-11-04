# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals

import os
import sys
import unittest
from couchdbkit import Server
from desk.utils import CouchdbUploader
import time
import json
from copy import copy
from dns.resolver import NXDOMAIN
from desk.plugin.base import MergedDoc, VersionDoc
from desk.plugin.dns.dnsbase import DnsValidator
from desk.plugin.dns.powerdns import Powerdns
from desk.utils import ObjectDict
from desk import Worker, Foreman


class WorkerTestCase(unittest.TestCase):
    def setUp(self):
        self.db_conf = {
            "couchdb_uri": "http://admin-test:admin-test@cdb_1:5984",
            "couchdb_db": "desk_tester",
        }
        self.conf = {
            "powerdns_backend": "sqlite",
            "powerdns_db": "/opt/local/etc/powerdns/dns.db",
            "powerdns_name": "dnsa_1.test.tt",
            "powerdns_primary": "dnsa_1.test.tt",
            "worker_is_foreman": True,
        }
        self.conf.update(self.db_conf)
        s = Server(self.db_conf["couchdb_uri"])
        self.s = s
        s.create_db(self.db_conf['couchdb_db'])
        self.db = self.s.get_db(self.db_conf["couchdb_db"])
        self.couch_up = CouchdbUploader(
            path=os.path.dirname(__file__),
            auth=('admin-test', 'admin-test'), **self.db_conf
        )
        status_code = self.couch_up.put(
            data="@fixtures/couchdb-design.json",
            doc_id="_design/{couchdb_db}"
        )
        if not status_code == 201:
            s.delete_db(self.db_conf["couchdb_db"])

        worker_id = "worker-localhost"
        d = {
            "_id": worker_id, "type": "worker", "hostname": "localhost",
            "provides": {
                "domain": [{"backend": "powerdns", "name": "dnsa_1.test.tt"}]
            }
        }
        self.assertTrue(
            self.couch_up.put(data=json.dumps(d), doc_id=worker_id) == 201
        )
        self.assertTrue(
            self.couch_up.put(data="@fixtures/couchdb-template-dns.json",
                        doc_id="template-email") == 201
        )
        self.assertTrue(
            self.couch_up.put(data="@fixtures/couchdb-map-ips.json",
                        doc_id="map-ips") == 201
        )

    def tearDown(self):
        has_domain1, has_domain2 = (
            Powerdns(ObjectDict(**self.conf)).check_domain("test.tt"),
            Powerdns(ObjectDict(**self.conf)).check_domain("test2.tt")
        )
        self._remove_domain("test.tt") if has_domain1 else None
        self._remove_domain("test2.tt") if has_domain2 else None
        self.s.delete_db(self.db_conf["couchdb_db"])

    def _run_order(self):
        self._run_worker(is_foreman=True)

    def _run_worker(self, is_foreman=True):
        conf = self.conf
        w = Foreman(conf, hostname="localhost")
        w.run_once()

    def _get_dns_validator(self, doc_id, lookup={
                           'dnsa_1.test.tt': "127.0.0.1",
                           'dnsb_1.test.tt': "127.0.0.1"
                           }):
        doc = MergedDoc(self.db, self.db.get(doc_id)).doc
        validator = DnsValidator(doc, lookup=lookup)
        return validator

    def _create_order_doc(self):
        current_time = time.localtime()
        order_id = "order-{}-{}".format(int(time.mktime(current_time)),
                                        self.s.next_uuid())

        order_doc = {
            "_id": order_id,
            "date": time.strftime("%Y-%m-%d %H:%M:%S %z", current_time),
            "type": "order", "sender": "pad", "state": "new_pre"
        }
        self.assertTrue(self.couch_up.put(data=json.dumps(order_doc),
                        doc_id=order_id) == 201)
        self.assertTrue(self.couch_up.update(handler='add-editor',
                        doc_id=order_id) == 201)
        return order_id

    def _add_domain_test_tt(self, run=True, add_order=True):
        dns_id = "dns-test.tt"
        self.assertTrue(self.couch_up.put(data="@fixtures/couchdb-dns-test.tt.json",
                        doc_id=dns_id) == 201)
        self.assertTrue(self.couch_up.update(handler='add-editor',
                        doc_id=dns_id) == 201)
        order_id = None
        if run and add_order:
            order_id = self._create_order_doc()
            self._run_order()
        return (dns_id, order_id)

    def _add_domain_test2_tt(self, run=True, add_order=True):
        dns_id = "dns-test2.tt"
        self.assertTrue(self.couch_up.put(data="@fixtures/couchdb-dns-test2.tt.json",
                        doc_id=dns_id) == 201)
        self.assertTrue(self.couch_up.update(handler='add-editor',
                        doc_id=dns_id) == 201)
        order_id = None
        if run and add_order:
            order_id = self._create_order_doc()
            self._run_order()
        return (dns_id, order_id)

    def _remove_domain(self, domain, docs=None):
        # cleanup
        pdns = Powerdns(ObjectDict(**self.conf))
        pdns.del_domain(domain)
        if docs:
            self.db.delete_doc(docs)

    def test_worker_settings(self):
        doc = self.db.get("worker-localhost")
        self.assertTrue(doc['provides']['domain'][0]["backend"] == "powerdns")

    def test_new_domain(self):
        dns_id, order_id = self._add_domain_test_tt()
        self.assertTrue(self.db.get(dns_id)['state'] == 'active')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, order_id])

    def test_update_record(self):
        dns_id, order_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        dns_doc['a'][4]['ip'] = "1.1.1.21"
        dns_doc['a'][1]['host'] = "ns3"
        dns_doc['cname'][0]['host'] = "dnsa_1"
        VersionDoc(self.db, dns_doc).create_version()
        order_id = self._create_order_doc()
        self._run_order()
        #import ipdb; ipdb.set_trace();
        self.assertTrue(self.db.get(dns_id)['state'] == 'active')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, order_id])

    def test_complete_change_record(self):
        dns_id, order_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        changed_a = copy(dns_doc['a'][4])
        dns_doc['a'][4]['ip'] = "1.1.1.21"
        dns_doc['a'][4]['host'] = "www2"
        VersionDoc(self.db, dns_doc).create_version()
        order_id = self._create_order_doc()
        self._run_order()
        self.assertTrue(self.db.get(dns_id)['state'] == 'active')
        self.assertFalse(
        #with self.assertRaises(NXDOMAIN):
            self._get_dns_validator('dns-test.tt').check_one_record(
                'A', 'ip', q_key='host', item=changed_a
            )
        )
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, order_id])

    def test_append_record(self):
        dns_id, order_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        dns_doc['a'].append({'host': "forum", 'ip': "1.1.1.25"})
        dns_doc['cname'].append({'alias': "super", 'host': "www"})
        VersionDoc(self.db, dns_doc).create_version()
        order_id = self._create_order_doc()
        self._run_order()
        self.assertTrue(self.db.get(dns_id)['state'] == 'active')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self._remove_domain('test.tt', docs=[dns_id, order_id])

    def test_delete_record(self):
        dns_id, order1_id = self._add_domain_test_tt()
        dns_doc = self.db.get(dns_id)
        removed_a = dns_doc['a'].pop(4)
        vd = VersionDoc(self.db, dns_doc)
        vd.create_version()
        order2_id = self._create_order_doc()
        self._run_order()
        self.assertTrue(self.db.get(dns_id)['state'] == 'active')
        self.assertFalse(
        #with self.assertRaises(NXDOMAIN):
            self._get_dns_validator('dns-test.tt').check_one_record(
                'A', 'ip', q_key='host', item=removed_a
            )
        )
        self._remove_domain('test.tt', docs=[dns_id, order1_id, order2_id])

    def test_two_domains(self):
        ddnsa_1_id, order_id = self._add_domain_test_tt(run=False, add_order=False)
        ddnsb_1_id, order_id = self._add_domain_test2_tt(run=False, add_order=False)
        order1_id = self._create_order_doc()
        self._run_order()
        self.assertTrue(self.db.get(ddnsa_1_id)['state'] == 'active')
        self.assertTrue(self._get_dns_validator('dns-test.tt').do_check())
        self.assertTrue(self.db.get(ddnsb_1_id)['state'] == 'active')
        self.assertTrue(self._get_dns_validator('dns-test2.tt').do_check())
        self._remove_domain('test.tt', docs=[ddnsa_1_id, order1_id])
        self._remove_domain('test2.tt', docs=[ddnsb_1_id])

if __name__ == '__main__':
    unittest.main()
