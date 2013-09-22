# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from StringIO import StringIO
from copy import copy
import json
import json_diff
import simplejson as json


class OptionsClassDiff(object):
    def __init__(self):
        self.exclude = [
            '_attachments', 'prev_rev', '_rev', 'state',
            'client_id', 'template_id', 'template_type'
        ]
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
        self.db.put_attachment(
            old_doc, json.dumps(old_doc),
            name=old_doc['_rev'], content_type="application/json"
        )
        new_doc_merged = self.db.get(self.doc['_id'])
        del self.doc['_rev']
        new_doc_merged.update(self.doc)
        self.doc = new_doc_merged
        self.db.save_doc(self.doc)


class Updater(object):
    def __init__(self, db, doc, service):
        self.db, self.doc = db, doc
        choose_task = {'new': service.create, 'changed': service.update}
        self.task = None
        if doc['state'] in choose_task:
            self.task = choose_task[doc['state']]
        self.merged_doc = MergedDoc(db, doc).doc
        if 'prev_rev' in doc:
            self.prev_doc = json.loads(
                db.fetch_attachment(doc['_id'], doc['prev_rev'])
            )
        else:
            self.prev_doc = None
        service.set_docs(self.merged_doc, self.prev_doc)
        if hasattr(service, 'map_doc_id'):
            lookup_map_doc = db.get(service.map_doc_id)
            service.set_lookup_map(lookup_map_doc)
        self.service = service
        if 'prev_rev' in doc and doc['state'] == 'changed':
            diff = self._create_diff()
            service.set_diff(diff)

    def _remove_attachment(self, doc):
        if '_attachments' in doc:
            doc = copy(doc)
            del doc['_attachments']
        return doc

    def _create_diff(self):
        diffator = json_diff.Comparator(
            StringIO(json.dumps(self._remove_attachment(self.prev_doc))),
            StringIO(json.dumps(self._remove_attachment(self.merged_doc))),
            opts=OptionsClassDiff()
        )
        diff = diffator.compare_dicts()
        diff_merged = {
            'update': {},
            'append': {},
            'remove': {}
        }
        for item in self.service.structure:  # TODO cleanup lot of duplication
            name, key_id, value_id = (
                item['name'], item['key_id'], item['value_id']
            )
            # an existing entry changed
            if ('_update' in diff and name in diff['_update']
               and '_update' in diff['_update'][name]):
                item_diff = diff['_update'][name]['_update']
                item_diff_merged = []
                for i in item_diff:
                    changes = item_diff[i]['_update']
                    # both changed, lookup via id of old entry
                    if value_id in changes and key_id in changes:
                        key, value, lookup = (
                            changes[key_id], self.doc[name][i][value_id], 'id'
                        )
                    # value changed, lookup key
                    elif value_id in changes:
                        key, value, lookup = (
                            self.doc[name][i][key_id], changes[value_id], 'key'
                        )
                    # key changed, lookup value
                    elif key_id in changes:
                        key, value, lookup = (
                            changes[key_id],
                            self.doc[name][i][value_id],
                            'value'
                        )
                    item_diff_merged.append(
                        {key_id: key, value_id: value, 'lookup': lookup}
                    )
                diff_merged['update'][name] = item_diff_merged
            # a new entry
            if ('_update' in diff and name in diff['_update']
               and '_append' in diff['_update'][name]):
                item_diff = diff['_update'][name]['_append']
                item_diff_merged = []
                for i in item_diff:
                    item_diff_merged.append(item_diff[i])
                diff_merged['append'][name] = item_diff_merged
            # delete entry
            if ('_update' in diff and name in diff['_update']
               and '_remove' in diff['_update'][name]):
                item_diff = diff['_update'][name]['_remove']
                item_diff_merged = []
                for i in item_diff:
                    item_diff_merged.append(item_diff[i])
                diff_merged['remove'][name] = item_diff_merged
        return diff_merged

    def do_task(self):
        was_successfull = False
        if self.task:
            was_successfull = self.task()
        return was_successfull


class FilesForCouch(object):
    def __init__(self, data, directory=None):
        self.data = data
        self.directory = directory

    def create_files(self):
        for filename, content in self.data:
            with open('{}/{}.json'.format(self.directory, filename), 'w') as outfile:
                content["nameservers"] = ", ".join(content["nameservers"])
                json.dump(content, outfile, indent=4)
