# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import ast
import os
import shutil
import ezodf
from couchdbkit import Server
from desk.command import SettingsCommand
from desk.plugin.extcrm.todoyu import Todoyu
from desk.utils import CouchdbUploader, FilesForCouch


class ImportServices(object):
    def __init__(self, settings):
        self.service_tpl = {'type': 'service', 'state': 'active'}
        self.docs, self.clients_extcrm_ids = [], {}
        self.settings = settings
        self.nr_cols = settings.nr_cols
        self.server = Server(self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)
        self.init_spreadsheet()

    def init_spreadsheet(self):
        spreadsheet = ezodf.opendoc(self.settings.src)
        sheet = spreadsheet.sheets[0]
        self.rows = sheet.rows()
        self.header = [
            c.value.lower() if hasattr(c.value, 'lower') else c.value
            for c in self.rows.next()[:self.nr_cols]
        ]

    def process_row(self, row):
        for service_type in ['web', 'email']:
            if row[service_type]:
                service_doc = self.service_tpl.copy()
                service_doc['_id'] = "service-%s" % self.server.next_uuid()
                if row['todoyu'] not in self.clients_extcrm_ids:
                    client_id = self.get_or_create_client(row)
                    self.clients_extcrm_ids[row['todoyu']] = client_id
                else:
                    client_id = self.clients_extcrm_ids[row['todoyu']]
                service_doc['service_type'] = service_type
                service_doc['start_date'] = row['start_date']
                service_doc['client_id'] = client_id
                if isinstance(row[service_type], dict):
                    service_doc.update(row[service_type])
                else:
                    service_doc['package'] = row[service_type]
                if row['%s_addons' % service_type]:
                    addons_key = '%s_addons' % service_type
                    service_doc['addons'] = row[addons_key]
                items_key = '%s_items' % service_type
                if items_key in row and row[items_key]:
                    items_key = '%s_items' % service_type
                    service_doc['items'] = row[items_key]
                self.docs.append((service_doc['_id'], service_doc))

    def process_sheet(self):
        services = []
        i = 0
        for row in self.rows:
            i += 1
            if any([cell.value for cell in row[:self.nr_cols]]):
                cell_values = []
                for cell in row[:self.nr_cols]:
                    cell_is_python = hasattr(cell.value, "startswith") and (
                        cell.value.startswith("{") or
                        cell.value.startswith("[")
                    )
                    if cell_is_python:
                        value = ast.literal_eval(cell.value)
                    else:
                        value = cell.value
                    cell_values.append(value)
                row_dict = dict(zip(self.header[:self.nr_cols], cell_values))
                services.append(row_dict)
            else:
                break
        return services

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def get_or_create_client(self, row):
        if row['org_name']:
            name = row['org_name']
        else:
            name = "%s %s" % (row['n_given'], row['n_family'])
        query_results = self.db.view(
            self._cmd("client_by_name"), key=name,
            include_docs=False
        )
        if query_results.count() == 1:
            client_doc = query_results.first()['value']
        elif query_results.count() == 0:
            client_doc = {'type': 'client'}
            client_doc['_id'] = 'client-%s' % self.server.next_uuid()
        else:
            raise
        client_doc['is_billable'] = 1
        client_doc['extcrm_id'] = row['todoyu']
        client_doc['name'] = name
        self.docs.append((client_doc['_id'], client_doc))

        return client_doc['_id']

    def create_docs(self):
        self.rows = self.process_sheet()
        self.todoyu = Todoyu(self.settings)
        self.dest = "{}/services_json".format(
            os.path.dirname(self.settings.src)
        )
        for row in self.rows:
            self.process_row(row)

    def create_files(self):
        self.create_docs()
        if os.path.exists(self.dest):
            shutil.rmtree(self.dest)
        os.mkdir(self.dest)
        json_files = FilesForCouch(self.docs, self.dest)
        json_files.create()

        if not self.settings.only_files:
            couch_up = CouchdbUploader(
                path=self.dest, couchdb_uri=self.settings.couchdb_uri,
                couchdb_db=self.settings.couchdb_db
            )

            for fname in os.listdir(self.dest):
                couch_up.put(
                    data="@{}".format(fname),
                    doc_id=fname[:-5]
                )
