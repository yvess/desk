# coding: utf-8
from __future__ import division
#from __future__ import unicode_literals
from __future__ import print_function

import os
import sys
sys.path.append("../")
import unittest
from couchdbkit import Server
from desk.utils import CouchdbUploader


class WorkerTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "couchdb_uri": "http://localhost:5984",
            "couchdb_db": "desk_tester",
        }
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
            raise Exception("Error with couchdb test database")

    def tearDown(self):
        self.s.delete_db(self.settings["couchdb_db"])

    def test_worker_settings(self):
        json = """
{
   "_id": "worker-tworker", "type": "worker", "hostname": "tworker",
   "provides": {
       "dns": [{ "backend": "powerdns", "server_type": "master"}]
   }
}
"""
        doc_id = "worker-tworker"
        status_code = self.up.put(data=json, doc_id=doc_id)
        self.assertTrue(status_code == 201)

        doc = self.db.get(doc_id)
        self.assertTrue(doc['provides']['dns'][0]["backend"] == "powerdns")

if __name__ == '__main__':
    unittest.main()
