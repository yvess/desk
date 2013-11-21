# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import ast
import os
import shutil
import ezodf
from couchdbkit import Server
from desk.cmd import SettingsCommand
from desk.plugin.base import FilesForCouch
from desk.plugin.extcrm.todoyu import Todoyu
from desk.utils import CouchdbUploader, create_order_doc, auth_from_uri


class ImportServiceCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        service_import_parser = subparsers.add_parser(
            'service-import',
            help="""import service data from odt""",
            description="Import service data odt, and load it into couch"
        )
        service_import_parser.add_argument(*config_parser['args'],
                                           **config_parser['kwargs'])
        service_import_parser.add_argument(
            "src", help="source of the odt file",
        )

        service_import_parser.add_argument(
            "-nr", "--nr-cols", type=int, dest="nr_cols", default=17,
            help="number of cols to read",
        )

        return service_import_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def _init_spreadsheet(self):
        spreadsheet = ezodf.opendoc(self.settings.src)
        sheet = spreadsheet.sheets[0]
        self.rows = sheet.rows()
        self.header = [
            c.value.lower() if hasattr(c.value, 'lower') else c.value
            for c in self.rows.next()[:self.nr_cols]
        ]

    def _process_sheet(self):
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

    def _init_couch(self):
        self.server = Server(self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)

    def _get_or_create_client(self, client):
        query_results = self.db.view(
            self._cmd("client_extcrm_id"), key=client['todoyu'],
            include_docs=False
        )
        if query_results.count() == 1:
            return query_results.first()['value']
        elif query_results.count() == 0:
            if client['org_name']:
                name = client['org_name']
            else:
                name = "%s %s" % (client['n_given'], client['n_family'])
            client_doc = {
                '_id':  'client-%s' % self.server.next_uuid(),
                'type': 'client', 'is_billable': 1,
                'extcrm_id': client['todoyu'],
                'name': name
            }
            self.docs.append((client_doc['_id'], client_doc))
            return client_doc['_id']
        else:
            raise

    def run(self):
        self.nr_cols = self.settings.nr_cols
        self._init_couch()
        self._init_spreadsheet()
        clients_extcrm_ids = {}
        client_services = self._process_sheet()
        service_tpl = {
            'type': 'service', 'state': 'active'
        }
        self.docs = []
        self.todoyu = Todoyu(self.settings)
        self.dest = "{}/services_json".format(os.path.dirname(self.settings.src))
        for client in client_services:
            for service_type in ['web', 'email']:
                if client[service_type]:
                    service_doc = service_tpl.copy()
                    service_doc['_id'] = "service-%s" % self.server.next_uuid()
                    service_doc['extcrm_id'] = client['todoyu']
                    if client['todoyu'] not in clients_extcrm_ids:
                        client_id = self._get_or_create_client(client)
                        clients_extcrm_ids[client['todoyu']] = client_id
                    else:
                        client_id = clients_extcrm_ids[client['todoyu']]
                    service_doc['service_type'] = service_type
                    service_doc['start_date'] = client['start_date']
                    service_doc['client_id'] = client_id
                    if isinstance(client[service_type], dict):
                        service_doc.update(client[service_type])
                    else:
                        service_doc['package'] = client[service_type]
                    if client['%s_addons' % service_type]:
                        addons_key = '%s_addons' % service_type
                        service_doc['addons'] = client[addons_key]
                    items_key = '%s_items' % service_type
                    if items_key in client and client[items_key]:
                        items_key = '%s_items' % service_type
                        service_doc['items'] = client[items_key]
                    self.docs.append((service_doc['_id'], service_doc))

        if os.path.exists(self.dest):
            shutil.rmtree(self.dest)
        os.mkdir(self.dest)
        json_files = FilesForCouch(self.docs, self.dest)
        json_files.create()

        co = CouchdbUploader(
            path=self.dest, couchdb_uri=self.settings.couchdb_uri,
            couchdb_db=self.settings.couchdb_db
        )

        for fname in os.listdir(self.dest):
            co.put(
                data="@{}".format(fname),
                doc_id=fname[:-5]
            )
