# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from StringIO import StringIO
from copy import copy, deepcopy
import logging
from couchdbkit.exceptions import ResourceNotFound
import json
import json_diff


class OptionsClassDiff(object):
    def __init__(self):
        self.exclude = [
            '_attachments', 'prev_rev', 'active_rev', 'prev_active_rev', '_rev', 'state',
            'client_id', 'template_id', 'template_type'
        ]
        self.include = []
        self.ignore_append = []


class MergedDoc(object):
    cache = {}

    def __init__(self, db, doc, cache_key=None):
        self.db = db
        if len(MergedDoc.cache.keys()) > 50:
            MergedDoc.cache = {}
        merged_doc = None
        empty_keys = []
        if 'template_id' in doc:
            merged_doc = deepcopy(self.get_template(doc['template_id'], cache_key))
            doc_no_empty = {}
            for item_key in doc.keys():
                if doc[item_key]:
                    doc_no_empty[item_key] = deepcopy(doc[item_key])
                else:
                    empty_keys.append(item_key)
            merged_doc.update(doc_no_empty)
            for key in empty_keys:
                if key in merged_doc and merged_doc['key']:
                    pass
                else:
                    merged_doc[key] = []
            del merged_doc['template_id']
        self.doc = merged_doc if merged_doc else doc

    def get_template(self, template_id, cache_key):
        if cache_key in MergedDoc.cache \
           and template_id in MergedDoc.cache[cache_key]:
            template_doc = MergedDoc.cache[cache_key][template_id]
        else:
            template_doc = self.db.get(template_id)
            if cache_key not in MergedDoc.cache:
                MergedDoc.cache[cache_key] = {}
            MergedDoc.cache[cache_key][template_id] = template_doc
        return template_doc


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
        self.db, self.doc, self.active_doc = db, doc, None
        choose_task = {
            'new': service.create,
            'changed': service.update,
            'delete': service.delete
        }
        self.task = None
        self.active_doc = None
        if doc['state'] in choose_task:
            self.task = choose_task[doc['state']]

        self.merged_doc = MergedDoc(db, doc).doc
        if 'active_rev' in doc:
            active_rev = doc['active_rev']
            active_doc_json = db.fetch_attachment(doc['_id'], active_rev)
            self.active_doc = MergedDoc(db, json.loads(active_doc_json)).doc
        service.set_docs(self.merged_doc, self.active_doc)
        if hasattr(service, 'map_doc_id'):
            try:
                lookup_map_doc = db.get(service.map_doc_id)
                service.set_lookup_map(lookup_map_doc)
            except ResourceNotFound:
                pass
        self.service = service
        if self.active_doc and doc['state'] == 'changed':
            diff = self._create_diff()
            service.set_diff(diff)

    def _remove_attachment(self, doc):
        if '_attachments' in doc:
            doc = copy(doc)
            del doc['_attachments']
        return doc

    def _create_diff(self):
        old_doc = self._remove_attachment(self.active_doc)
        new_doc = self._remove_attachment(self.doc)
        old_doc_string = json.dumps(old_doc)
        new_doc_string = json.dumps(new_doc)
        diffator = json_diff.Comparator(
            StringIO(old_doc_string),
            StringIO(new_doc_string),
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
                    for v_id in value_id.split(','):
                        changes = item_diff[i]['_update']
                        # both changed, lookup via id of old entry
                        if v_id in changes and key_id in changes:
                            key, value, lookup = (
                                changes[key_id], self.doc[name][i][v_id], 'id'
                            )
                        # value changed, lookup key
                        elif v_id in changes:
                            key, value, lookup = (
                                self.doc[name][i][key_id], changes[v_id], 'key'
                            )
                        # key changed, lookup value
                        elif key_id in changes:
                            key, value, lookup = (
                                changes[key_id],
                                self.doc[name][i][v_id],
                                'value'
                            )
                        if v_id in changes or key_id in changes:
                            item_diff_merged.append(
                                {key_id: key, v_id: value, 'lookup': lookup}
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
