# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import ast
import os
import shutil
import ezodf
from couchdbkit import Server
from desk.command import SettingsCommand
from desk.utils import get_crm_module
from desk.plugin.extcrm.todoyu import Todoyu
from desk.utils import CouchdbUploader, FilesForCouch


class QueryServices(object):
    def __init__(self, settings):
        self.clients_extcrm_ids = {}
        self.settings = settings
        self.server = Server(self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)
        self.crm = get_crm_module(self.settings)

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def get_services(self):
        services = []
        startkey = [self.settings.service]
        endkey = [self.settings.service]
        only_billable = self.settings.only_billable

        if self.settings.service_packages:
            startkey.append(self.settings.service_packages)
            endkey.append(self.settings.service_packages)
        else:
            endkey.append({})

        if self.settings.service_addons:
            startkey.append(self.settings.service_addons)
            endkey.append(self.settings.service_addons)
        else:
            endkey.append({})

        for item in self.db.view(
                self._cmd("service_package_addon"),
                startkey=startkey, endkey=endkey, include_docs=True):
            if 'extcrm_id' in item['doc']:
                extcrm_id = item['doc']['extcrm_id']
                service_name = '-'.join([part for part in item['key'] if part])
                included_items = []
                if 'value' in item and 'included_service_items' in item['value']:
                    included_items = [included['itemid'] for included in item['value']['included_service_items']]
                included_items = ','.join(included_items)
                address_id = item['doc']['extcrm_id'] if 'extcrm_id' in item['doc'] else None
                contact_id = item['doc']['extcrm_contact_id'] if 'extcrm_contact_id' in item['doc'] else None
                if address_id and self.crm.has_contact(contact_id):
                    contact = self.crm.get_contact(contact_id)
                    print(
                        contact.email, ';' ,
                        contact.name, ';',
                        service_name, ';',
                        included_items, ';',
                        extcrm_id,
                        sep=''
                    )
                else:
                    print(
                        "# No Email #", ';' ,
                        "# no contact#", ';',
                        service_name, ';',
                        included_items, ';',
                        extcrm_id,
                        sep=''
                    )
            else:
                print("*** no extcrm_id", item)
        return services
