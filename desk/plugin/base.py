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
        self.service = service
        if 'prev_rev' in doc and doc['state'] == 'changed':
            service.set_diff(self._create_diff())

    def _prepare_docs(self, doc, prev_doc):
        for key in ['_attachments', '_rev']:
            if key in doc:
                del doc[key]
            if key in doc:
                del prev_doc[key]
        return (doc, prev_doc)

    def _create_diff(self):
        prev_doc = json.loads(self.db.fetch_attachment(self.doc['_id'], self.doc['prev_rev']))
        doc = MergedDoc(self.db, self.doc).doc
        doc, prev_doc = self._prepare_docs(doc, prev_doc)
        diffator = json_diff.Comparator(StringIO(json.dumps(prev_doc)), StringIO(json.dumps(doc)), opts=OptionsClassDiff())
        diff = diffator.compare_dicts()
        diff_merged = {'update': {}}
        for item in self.service.structure:
            name, key_id, value_id = item['name'], item['key_id'], item['value_id']
            if '_update' in diff and name in diff['_update']:
                item_diff = diff['_update'][name]['_update']
                item_diff_merged = []
                for i in item_diff:
                    if value_id in item_diff[i]['_update']:
                        key, value, lookup = doc[name][i][key_id], item_diff[i]['_update'][value_id], 'key'
                    else:
                        key, value, lookup = item_diff[i]['_update'][key_id], doc[name][i][value_id], 'value'
                    item_diff_merged.append({key_id: key, value_id: value, 'lookup': lookup}
                    )
                diff_merged['update'][name] = item_diff_merged
        return diff_merged

    def do_task(self):
        self.task()
        self.doc['state'] = 'live'
        self.db.save_doc(self.doc)
