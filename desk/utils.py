# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals
import sys
sys.path.append("../")
import requests


class ObjectDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


class CouchdbUploader(object):
    def __init__(self, couchdb_uri=None, couchdb_db=None, path=None, auth=()):
        self.uri = couchdb_uri
        self.db = couchdb_db
        self.path = path
        self.auth = auth
        if couchdb_uri.count('@') == 1:
            self.auth = tuple(couchdb_uri.split("@")[0].split('//')[1].split(":"))
            print("auth", self.auth)


    def put(self, data, doc_id, only_status=True):
        if data[0] == "@":
            filename = "{}/{}".format(self.path, data[1:])
            with open(filename, "r") as f:
                data = "".join([l.strip() for l in f.readlines() if not l.strip().find("//") == 0])  # remove comments in json
        url = "{}/{}/{}".format(self.uri, self.db, doc_id.format(couchdb_db=self.db))
        r = requests.put(url, data=data,
            headers={'Content-type': 'application/json', 'Accept': 'text/plain'},  auth=self.auth
        )
        return r.status_code if only_status else r

    def update(self, handler, doc_id, only_status=True):
        r = requests.put("{}/{}/_design/{}/_update/{}/{}".format(self.uri, self.db, self.db, handler, doc_id.format(couchdb_db=self.db)),
            headers={'Content-type': 'application/json', 'Accept': 'text/plain'},  auth=self.auth
        )
        return r.status_code if only_status else r
