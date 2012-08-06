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


class UtilTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "couchdb_uri": "http://localhost:5984",
            "couchdb_db": "desk_tester",
        }
        s = Server()
        self.s = s
        s.create_db(self.settings['couchdb_db'])
        self.up = CouchdbUploader(path=os.path.dirname(__file__), **self.settings)

    def tearDown(self):
        self.s.delete_db(self.settings["couchdb_db"])

    def test_broken_json(self):
        json = """ { "_id": "broken-json", "type": "worker", "hostname": "tworkerbroken", } """  # no ","
        status_code = self.up.put(data=json, doc_id="borken-json")
        self.assertTrue(status_code == 400)

if __name__ == '__main__':
    unittest.main()
