# coding: utf-8
from __future__ import division
#from __future__ import unicode_literals
from __future__ import print_function

import sys
sys.path.append("../")

import requests


class ObjectDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


class CouchdbUploader(object):
    def __init__(self, couchdb_uri=None, couchdb_db=None, path=None):
        self.uri = couchdb_uri
        self.db = couchdb_db
        self.path = path

    def put(self, data, doc_id):
        if data[0] == "@":
            filename = "{}/{}".format(self.path, data[1:])
            with open(filename, "r") as f:
                data = "".join([l.strip() for l in f.readlines() if not l.strip().find("//") == 0])  # remove comments in json
        r = requests.put("{}/{}/{}".format(self.uri, self.db, doc_id.format(couchdb_db=self.db)), data=data,
            headers={'Content-type': 'application/json', 'Accept': 'text/plain'}
        )
        return r.status_code
