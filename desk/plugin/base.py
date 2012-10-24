# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from StringIO import StringIO
import json
import json_diff


class OptionsClassDiff(object):
    def __init__(self):
        self.exclude = ['_attachments', 'prev_rev', '_rev', 'state', 'client_id', 'template_id']
        self.include = []
        self.ignore_append = []


class MergedDoc(object):
    def __init__(self, db, doc):
        merged_doc = None
        if 'template_id' in doc:
            merged_doc = db.get(doc['template_id'])
            merged_doc.update(doc)
            del merged_doc['template_id']
        self.doc = merged_doc if merged_doc else doc


class Updater(object):
    def __init__(self, db, doc, service):
        choose_task = {'new': service.create, 'changed': service.update}
        self.task = choose_task[doc['state']]
        self.merged_doc = MergedDoc(db, doc).doc
        service.set_doc(self.merged_doc)
        if 'prev_rev' in doc and choose_task == service.update:
            service.set_diff(self._create_diff())
        self.db, self.doc = db, doc

#    def _doc_for_diff(self, doc):
#        cleaned_doc = doc.copy()
#        for key in ['_attachments', 'prev_rev', '_rev', 'state', 'client_id', 'template_id']:  # TODO: what todo with template_id?
#            if key in cleaned_doc:
#                del cleaned_doc[key]
#        return cleaned_doc#

    def _merge_update_diff(diff):
        return diff

    def _create_diff(self):
        prev_doc = json.loads(self.db.fetch_attachment(self.doc['_id'], self.doc['prev_rev']))
        diffator = json_diff.Comparator(StringIO(json.dumps(prev_doc)), StringIO(json.dumps(self.doc)), opts=OptionsClassDiff())
        diff = diffator.compare_dicts()
        diff['_update'] = self._merge_update_diff(diff['_update'])
        return diff

    def do_task(self):
        self.task()
        self.doc['state'] = 'live'
        self.db.save_doc(self.doc)
