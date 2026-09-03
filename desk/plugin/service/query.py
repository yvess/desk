from desk.utils import get_crm_module


class QueryServices(object):
    def __init__(self, settings, db):
        self.clients_extcrm_ids = {}
        self.settings = settings
        self.db = db
        self.crm = get_crm_module(self.settings)

    def query(self):
        services = []
        startkey = [self.settings.service]
        endkey = [self.settings.service]
        only_billable = self.settings.only_billable

        if self.settings.service_packages:
            startkey.append(self.settings.service_packages)
            endkey.append(self.settings.service_packages)
            couchdb_view = 'service_package_addon'
        else:
            couchdb_view = 'service_addon'

        if self.settings.service_addons:
            startkey.append(self.settings.service_addons)
            endkey.append(self.settings.service_addons)
        else:
            if self.settings.service_packages:
                couchdb_view = 'service_package_addon'
                endkey.append({})
            else:
                couchdb_view = 'service_type'
        for item in self.db.view(
                couchdb_view,
                startkey=startkey, endkey=endkey, include_docs=True):
            # the view links the client doc; it is null once the client is deleted
            client_doc = item.get('doc') or {}
            if 'extcrm_id' in client_doc:
                if client_doc.get('state') == 'deleted':
                    continue
                extcrm_id = client_doc['extcrm_id']
                service_name = '-'.join([part for part in item['key'] if part])
                included_items = []
                is_billable = client_doc['is_billable'] if 'is_billable' in client_doc else False
                if 'value' in item and 'included_service_items' in item['value']:
                    included_items = [
                        included['itemid'] for included in item['value']['included_service_items']
                    ]
                included_items = ','.join(included_items)
                address_id = client_doc['extcrm_id'] if 'extcrm_id' in client_doc else None
                if 'extcrm_contact_id' in client_doc and client_doc['extcrm_contact_id']:
                    contact_id = client_doc['extcrm_contact_id']
                elif 'p' in extcrm_id:
                    for part in extcrm_id.split('-'):
                        if part.startswith('p'):
                            contact_id = part
                else:
                    contact_id = ''

                if not only_billable or only_billable and is_billable:
                    if address_id and all([
                        self.crm.has_contact(cid.strip()) for cid in contact_id.split(',')
                    ]):
                        contacts = [
                            self.crm.get_contact(cid.strip()) for cid in contact_id.split(',')
                        ]
                        services.append([
                            ','.join([contact.email for contact in contacts]),
                            ','.join([contact.name for contact in contacts]),
                            service_name,
                            included_items,
                            extcrm_id, contact_id
                        ])
                    else:
                        services.append([
                            "# No Email #", "# no contact#", service_name,
                            included_items,
                            extcrm_id, ''
                        ])
            else:
                print("*** no extcrm_id", item)
        for service in services:
            print(';'.join(service))
        print("total: %s" % len(services))
