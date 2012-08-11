# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals


class Updater(object):
    def __init__(self, db, doc, service):
        self.service = service
        if doc['state'] == 'created':
            self.task = service.create
        if 'template_id' in doc:
            base_doc = db.get(doc['template_id'])
            base_doc.update(doc)
        self.doc = base_doc
        self.db = db

    def do_task(self):
        self.task()
        self.doc['state'] = 'live'
        self.db.save_doc(self.doc)
