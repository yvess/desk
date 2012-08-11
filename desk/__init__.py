# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division

import os
import sys
from couchdbkit import Server, Consumer
from couchdbkit.changes import ChangesStream
sys.path.append("../")
from desk.utils import ObjectDict
from desk.plugin import dns
from desk.pluginbase import Updater


class Worker(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.db = Server(uri=settings.couchdb_uri)[settings.couchdb_db]
        self.hostname = hostname
        self.provides = {}
        self.settings = settings
        self._setup_worker()

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
                        updater = Updater(self.db, doc, ServiceClass())
                        updater.do_task()
        else:
            raise

    def _process_queue(self, queue):
        for notification in queue:
            for task in self.db.view(self._cmd("todo")):
                doc = task['value']
                self._exec_task(doc)

    def run(self):
        with ChangesStream(self.db, feed="continuous", heartbeat=True,
            filter=self._cmd("queue")) as queue:
            self._process_queue(queue)

    def once(self):
        c = Consumer(self.db)
        queue = c.fetch(since=0, filter=self._cmd("queue"))['results']
        if queue:
            self._process_queue(queue)
