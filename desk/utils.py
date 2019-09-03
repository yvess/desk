
import time
from datetime import date, datetime
import uuid
import os
import shutil
import json
import requests
import requests_async
import re
from urllib.parse import urljoin
from importlib import import_module


class ObjectDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


class CouchdbUploader(object):
    def __init__(self, couchdb_uri=None, couchdb_db=None, path=None, auth=()):
        self.uri = couchdb_uri
        self.db = couchdb_db
        self.path = path
        self.auth = auth
        if couchdb_uri.count('@') == 1:
            self.auth = auth_from_uri(couchdb_uri)

    def put(self, data, doc_id, only_status=True):
        if data[0] == "@":
            filename = "{}/{}".format(self.path, data[1:])
            with open(filename, "r") as f:
                # remove comments in json
                data = "".join([
                    l.strip() for l in f.readlines() if not (
                        l.strip().find("//") == 0
                    )
                ])
        url = "{}/{}/{}".format(
            self.uri, self.db, doc_id.format(couchdb_db=self.db)
        )
        r = requests.put(
            url, data=data,
            headers={
                'Content-type': 'application/json',
                'Accept': 'text/plain'
            },
            auth=self.auth
        )
        return r.status_code if only_status else r

    def update(self, handler, doc_id, only_status=True):
        r = requests.put(
            "{}/{}/_design/{}/_update/{}/{}".format(
                self.uri, self.db, self.db, handler,
                doc_id.format(couchdb_db=self.db)
            ),
            headers={
                'Content-type': 'application/json', 'Accept': 'text/plain'
            },
            auth=self.auth
        )
        return r.status_code if only_status else r


class FilesForCouch(object):
    def __init__(self, data, directory, prefix="", use_id_in_data=False):
        self.data = data
        self.directory = directory
        self.prefix = "{}-".format(prefix) if prefix else ""
        self.use_id_in_data = use_id_in_data

    def create(self):
        for filename, content in self.data:
            if self.use_id_in_data:
                file_parts = self.directory, self.prefix, content['_id']
            else:
                file_parts = self.directory, self.prefix, filename
            with open('{}/{}{}.json'.format(*file_parts), 'w') as outfile:
                json.dump(content, outfile, indent=4)


class CreateJsonFiles(object):
    def __init__(self, path, docs, couchdb_uri=None, couchdb_db=None):
        self.path, self.docs, self.couchdb_uri = path, docs, couchdb_uri
        self.create_files()
        if couchdb_uri and couchdb_db:
            self.upload()

    def create_files(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        os.mkdir(self.path)
        json_files = FilesForCouch(self.docs, self.path)
        json_files.create()

    def upload(self):
        couch_up = CouchdbUploader(
            path=self.path, couchdb_uri=self.couchdb_uri,
            couchdb_db=self.couchdb_db
        )

        for fname in os.listdir(self.path):
            couch_up.put(
                data="@{}".format(fname),
                doc_id=fname[:-5]
            )


class CouchDBSessionMixin:
    base_url = None

    def __init__(self, base_url=None, auth=None, db_name=None):
        self.base_url = base_url
        self.db_name = db_name
        super().__init__()
        self.auth = auth

    @classmethod
    def _basic_base_url(cls, couchdb_uri):
        proto, user, password, host, port = re.split("://|:|@",couchdb_uri)
        base_url = f'{proto}://{host}:{port}/'
        auth = (user, password)
        return base_url, auth

    @classmethod
    def db(cls, couchdb_uri=None, db_name=None):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}/'
        return cls(base_url, auth, db_name)

    @classmethod
    def db_design(cls, couchdb_uri=None, db_name=None):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}/_design/{db_name}/'
        return cls(base_url, auth, db_name)

    def request(self, method, url, *args, **kwargs):
        url = self.create_url(url)
        print('normal request url', url)
        response = super().request(
            method, url, *args, **kwargs
        )
        if 'ETag' in response.headers: # set couchdb rev in respone
            response.rev = response.headers['ETag'].replace('"','')
        else:
            response.rev = None
        return response

    def rev(self, url):
        url = self.create_url(url)
        response = self.request('head', url)
        return response.rev

    def create_url(self, url):
        return urljoin(self.base_url, url)


class CouchDBSession(CouchDBSessionMixin, requests.Session):
    pass


class CouchDBSessionAsync(CouchDBSessionMixin, requests_async.Session):
    async def request(self, method, url, *args, **kwargs):
        url = self.create_url(url)
        print('async request url', url)
        response = await super(requests_async.Session, self).request(
            method, url, *args, **kwargs
        )
        if 'ETag' in response.headers: # set couchdb rev in respone
            response.rev = response.headers['ETag'].replace('"','')
        else:
            response.rev = None
        return response

    async def rev(self, url):
        url = self.create_url(url)
        response = await self.request('head', url)
        return response.rev


def auth_from_uri(uri):
    return tuple(uri.split("@")[0].split('//')[1].split(":"))


def create_order_doc(uploader):
    now = datetime.now()
    # same format as javascript
    current_time = "%s.%sZ" % (now.strftime('%Y-%m-%dT%H:%M:%S'), "%03.0f" % (now.microsecond / 1000.0))
    order_id = "order-{}".format(str(uuid.uuid1()).replace('-',''))

    order_doc = {
        "_id": order_id,
        "date": current_time,
        "type": "order", "sender": "pad", "state": "new"
    }
    uploader.put(data=json.dumps(order_doc), doc_id=order_id)
    uploader.update(handler='add-editor', doc_id=order_id)
    return order_id


def parse_date(date_string, force_day=None):
    year, month, day = [int(item) for item in date_string.split("-")]
    if force_day == 'start':
        day = 1
    return date(year, month, day)


def calc_esr_checksum(ref_number):
    ref_number = str(int(ref_number))  # removed leading zeros
    quasigroup_esr = (0, 9, 4, 6, 8, 2, 7, 1, 3, 5)
    sum = 0

    for n in ref_number:
        sum = quasigroup_esr[(sum + int(n)) % 10]
    return (10 - sum) % 10


def get_crm_module(settings):
    crm_module = import_module('.extcrm', package='desk.plugin')
    if 'worker_extcrm' in settings:
        crm_classname = settings.worker_extcrm.split(':')[0].title()
        Crm = getattr(crm_module, crm_classname)
        crm = Crm(settings)
    else:
        Crm = getattr(crm_module, 'Dummy')
        crm = Crm()
    return crm
