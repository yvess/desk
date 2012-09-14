# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals


class Updater(object):
    def __init__(self, db, doc, service):
        choose_task = {'created': service.create, 'live': service.update}
        self.task = choose_task[doc['state']]
        if 'template_id' in doc:
            merged_doc = db.get(doc['template_id'])
            merged_doc.update(doc)
        self.merged_doc = merged_doc
        service.set_doc(merged_doc)
        self.doc = doc
        self.db = db

    def do_task(self):
        self.task()
        #self.doc['state'] = 'live'
        #self.db.save_doc(self.doc)
