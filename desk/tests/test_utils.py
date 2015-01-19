# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals

import os
import sys
import unittest
from couchdbkit import Server
from desk.utils import CouchdbUploader


class UtilTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "couchdb_uri": "http://admin:admin@cdb:5984",
            "couchdb_db": "desk_tester",
        }
        s = Server(self.settings["couchdb_uri"])
        self.s = s
        s.create_db(self.settings['couchdb_db'])
        self.up = CouchdbUploader(path=os.path.dirname(__file__), auth=('admin', 'admin'), **self.settings)

    def tearDown(self):
        self.s.delete_db(self.settings["couchdb_db"])

    def test_broken_json(self):
        json = """ { "_id": "broken-json", "type": "worker", "hostname": "tworkerbroken", } """  # no ","
        status_code = self.up.put(data=json, doc_id="broken-json")
        self.assertTrue(status_code == 400)

if __name__ == '__main__':
    unittest.main()
