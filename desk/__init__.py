# coding: utf-8
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import os
import sys
from couchdbkit import Server
from couchdbkit.changes import ChangesStream
sys.path.append("../")
from desk.plugin import dns


class Worker(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        self.settings = settings
        self.db = Server(uri=settings.couchdb_uri)[settings.couchdb_db]
        self.hostname = hostname
        self.provides = {}

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def _setup_worker(self):
        for worker in self.db.list(self._cmd("list_docs"),
            "worker", include_docs=True,
            startkey=self.hostname, endkey=self.hostname):
            self.provides = worker['provides']

    def _exec_task(self, doc):
        if doc['type'] in self.provides:
            for service_settings in self.provides[doc['type']]:
                if 'server_type' in service_settings \
                and 'master' in service_settings['server_type'] \
                or not ('server_type' in service_settings):
                    #print(doc['type'], service_settings['backend'])
                    ServiceClass = None
                    doc_type = doc['type']
                    backend = service_settings['backend']
                    try:
                        ServiceClass = getattr(getattr(globals()[doc_type], backend), backend.title())
                    except AttributeError:
                        print("not found")
                    if ServiceClass:
                        #print(type(ServiceClass), ServiceClass)
                        service = ServiceClass(doc)
                        service.update()
        else:
            raise

    def run(self):
        self._setup_worker()
        with ChangesStream(self.db, feed="continuous", heartbeat=True,
            filter=self._cmd("queue")) as queue:
            for notification in queue:
                print("notification", notification)
                for task in self.db.view(self._cmd("todo")):
                    self._exec_task(task['value'])
