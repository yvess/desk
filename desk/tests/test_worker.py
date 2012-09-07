# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals

import os
import sys
sys.path.append("../")
import unittest
from couchdbkit import Server, Consumer
from desk.utils import CouchdbUploader
import time
import json


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
            data="@fixture-couchdb-design.json",
            doc_id="_design/{couchdb_db}"
        )
        if not status_code == 201:
            s.delete_db(self.settings["couchdb_db"])
            raise Exception("Error with couchdb test database, http code:{}".format(status_code))

        worker_id = "worker-localhost"
        d = {
           "_id": worker_id, "type": "worker", "hostname": "localhost",
           "provides": {
               "dns": [{"backend": "powerdns", "server_type": "master"}]
           }
        }
        self.assertTrue(self.up.put(data=json.dumps(d), doc_id=worker_id) == 201)

    def tearDown(self):
        self.s.delete_db(self.settings["couchdb_db"])

    def test_worker_settings(self):
        doc = self.db.get("worker-localhost")
        self.assertTrue(doc['provides']['dns'][0]["backend"] == "powerdns")

    def test_queue(self):
        template_id = "template-email-rackspace-hosting"
        self.assertTrue(self.up.put(data="@fixture-couchdb-template-dns.json", doc_id=template_id) == 201)

        dns_id = "dns-yas.ch"
        self.assertTrue(self.up.put(data="@fixture-couchdb-dns-yas.json", doc_id=dns_id) == 201)

        current_time = time.localtime()
        queue_id = "queue-{}".format(time.strftime("%Y-%m-%d_%H:%M:%S_%z", current_time))
        d = {
            "_id": queue_id,
            "date": time.strftime("%Y-%m-%d %H:%M:%S %z", current_time),
            "sender": "pad", "type": "queue", "state": "created"
        }
        self.assertTrue(self.up.put(data=json.dumps(d), doc_id=queue_id) == 201)

        from desk.worker import Worker
        
        w = Worker(self.conf, hostname="localhost")
        # w.once() # TODO make queue test work
        # self.assertTrue(self.db.get(dns_id)['state'] == 'live')
        # cleanup test
        self.db.delete_doc([dns_id, queue_id])

if __name__ == '__main__':
    unittest.main()
