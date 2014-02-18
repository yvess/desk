# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import ast
import os
import shutil
import ezodf
from couchdbkit import Server
from desk.cmd import SettingsCommand
from desk.plugin.extcrm.todoyu import Todoyu
from desk.utils import CouchdbUploader, FilesForCouch


class ImportServices(object):
    def __init__(self):
        self.service_tpl = {'type': 'service', 'state': 'active'}
        self.docs, self.clients_extcrm_ids = [], {}

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
                service_doc['extcrm_id'] = row['todoyu']
                if row['todoyu'] not in self.clients_extcrm_ids:
                    client_id = self.get_or_create_client(row)
                    self.clients_extcrm_ids[row['todoyu']] = client_id
                else:
                    client_id = self.clients_extcrm_ids[row['todoyu']]
                service_doc['service_type'] = service_type
                service_doc['start_date'] = row['start_date']
                service_doc['last_invoice_end_date'] = row[
                    'last_invoice_end_date'
                ]
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

    def init_couch(self):
        self.server = Server(self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)

    def get_or_create_client(self, row):
        query_results = self.db.view(
            self._cmd("client_extcrm_id"), key=row['todoyu'],
            include_docs=False
        )
        if query_results.count() == 1:
            return query_results.first()['value']
        elif query_results.count() == 0:
            if row['org_name']:
                name = row['org_name']
            else:
                name = "%s %s" % (row['n_given'], row['n_family'])
            client_doc = {
                '_id':  'client-%s' % self.server.next_uuid(),
                'type': 'client', 'is_billable': 1,
                'extcrm_id': row['todoyu'],
                'name': name
            }
            self.docs.append((client_doc['_id'], client_doc))
            return client_doc['_id']
        else:
            raise

    def create_docs(self):
        # self.nr_cols = self.settings.nr_cols
        # self.init_couch()
        # self.init_spreadsheet()
        self.rows = self.process_sheet()
        self.todoyu = Todoyu(self.settings)
        self.dest = "{}/services_json".format(
            os.path.dirname(self.settings.src)
        )
        self.create_services()

    def create_services_files(self):
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
