# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from StringIO import StringIO
from copy import copy
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


class VersionDoc(object):
    def __init__(self, db, doc):
        self.db = db
        self.doc = doc

    def create_version(self):
        old_doc = self.db.get(self.doc['_id'])
        old_doc = MergedDoc(self.db, old_doc).doc
        self.doc['state'] = 'changed'
        self.doc['prev_rev'] = old_doc['_rev']
        self.db.put_attachment(old_doc, json.dumps(old_doc), name=old_doc['_rev'], content_type="application/json")
        new_doc_merged = self.db.get(self.doc['_id'])
        del self.doc['_rev']
        new_doc_merged.update(self.doc)
        self.doc = new_doc_merged
        self.db.save_doc(self.doc)


class Updater(object):
    def __init__(self, db, doc, service):
        self.db, self.doc = db, doc
        choose_task = {'new': service.create, 'changed': service.update}
        self.task = choose_task[doc['state']]
        self.merged_doc = MergedDoc(db, doc).doc
        service.set_doc(self.merged_doc)
        if 'prev_rev' in doc and doc['state'] == 'changed':
            service.set_diff(self._create_diff())

#    def _doc_for_diff(self, doc):
#        cleaned_doc = doc.copy()
#        for key in ['_attachments', 'prev_rev', '_rev', 'state', 'client_id', 'template_id']:  # TODO: what todo with template_id?
#            if key in cleaned_doc:
#                del cleaned_doc[key]
#        return cleaned_doc#

    # def _merge_update_diff(self, diff):
    #     def rm_update(update_dict):
    #         if hasattr(update_dict, 'viewkeys'):
    #             update_dict = rm_update(update_dict[list(update_dict.viewkeys())[0]])
    #         return update_dict
    #     diff = rm_update(diff)
    #     print("DIFF", diff)
    #     return diff

    def _prepare_docs(self, doc, prev_doc):
        for key in ['_attachments', '_rev']:
            if key in doc:
                del doc[key]
            if key in doc:
                del prev_doc[key]
        return (doc, prev_doc)

    def _create_diff(self):
        prev_doc = json.loads(self.db.fetch_attachment(self.doc['_id'], self.doc['prev_rev']))
        doc = copy(self.doc)
        doc, prev_doc = self._prepare_docs(doc, prev_doc)
        diffator = json_diff.Comparator(StringIO(json.dumps(prev_doc)), StringIO(json.dumps(doc)), opts=OptionsClassDiff())
        diff = diffator.compare_dicts()
        a_diff = diff['_update']['a']['_update']
        diff_merged = {'update': {}}
        a_diff_merged = []
        for i in a_diff:
            a_diff_merged.append({'host': doc['a'][i]['host'], 'ip': a_diff[i]['_update']['ip']})
        diff_merged['update']['a'] = a_diff_merged
        diff_merged['update']['cname'] = []
        diff_merged['update']['mx'] = []
        return diff_merged

    def do_task(self):
        self.task()
        self.doc['state'] = 'live'
        self.db.save_doc(self.doc)
