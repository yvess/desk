# coding: utf-8
from __future__ import absolute_import, print_function, division  # unicode_literals
import time
from datetime import date
import json
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
            self.auth = auth_from_uri(couchdb_uri)

    def put(self, data, doc_id, only_status=True):
        if data[0] == "@":
            filename = "{}/{}".format(self.path, data[1:])
            with open(filename, "r") as f:
                # remove comments in json
                data = "".join([
                    l.strip() for l in f.readlines() if not (
                        l.strip().find("//") == 0
                    )
                ])
        url = "{}/{}/{}".format(
            self.uri, self.db, doc_id.format(couchdb_db=self.db)
        )
        r = requests.put(
            url, data=data,
            headers={
                'Content-type': 'application/json',
                'Accept': 'text/plain'
            },
            auth=self.auth
        )
        return r.status_code if only_status else r

    def update(self, handler, doc_id, only_status=True):
        r = requests.put(
            "{}/{}/_design/{}/_update/{}/{}".format(
                self.uri, self.db, self.db, handler,
                doc_id.format(couchdb_db=self.db)
            ),
            headers={
                'Content-type': 'application/json', 'Accept': 'text/plain'
            },
            auth=self.auth
        )
        return r.status_code if only_status else r


def auth_from_uri(uri):
    return tuple(uri.split("@")[0].split('//')[1].split(":"))


def create_order_doc(uploader):
    current_time = time.localtime()
    order_id = "order-{}".format(int(time.mktime(current_time)))

    order_doc = {
        "_id": order_id,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %z", current_time),
        "type": "order", "sender": "pad", "state": "new"
    }
    uploader.put(data=json.dumps(order_doc), doc_id=order_id)
    uploader.update(handler='add-editor', doc_id=order_id)
    return order_id


def parse_date(date_string):
    return date(*[int(item) for item in date_string.split("-")])
