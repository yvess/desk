
import time
from datetime import date, datetime
import uuid
import os
import shutil
import json
import requests
import requests_async
from aiohttp import client
from aiohttp import BasicAuth
import re
import collections
from json import JSONEncoder
from urllib.parse import urljoin
from importlib import import_module


class ObjectDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

class JSONDefaultDictEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

# from https://github.com/obspy/obspy/blob/master/obspy/core/util/AttributeDict.py
class AttributeDict(collections.abc.MutableMapping):
    defaults = {}
    readonly = []
    warn_on_non_default_key = False
    do_not_warn_on = []
    _types = {}

    def __init__(self, *args, **kwargs):
        self.__dict__.update(self.defaults)
        self.update(dict(*args, **kwargs))

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    def __getitem__(self, name, default=None):
        try:
            return self.__dict__[name]
        except KeyError:
            if name in self.defaults:
                return self.defaults[name]
            if default is None:
                raise
            return default

    def __setitem__(self, key, value):
        if key in self.readonly:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        if self.warn_on_non_default_key and key not in self.defaults:
            if key in self.do_not_warn_on:
                pass
            else:
                msg = ('Setting attribute "{}" which is not a default '
                       'attribute ("{}").').format(
                    key, '", "'.join(self.defaults.keys()))
                warnings.warn(msg)
        if key in self._types and not isinstance(value, self._types[key]):
            value = self._cast_type(key, value)

        mapping_instance = isinstance(value,
                                      collections.abc.Mapping)
        attr_dict_instance = isinstance(value, AttributeDict)
        if mapping_instance and not attr_dict_instance:
            self.__dict__[key] = AttributeDict(value)
        else:
            self.__dict__[key] = value

    def __delitem__(self, name):
        del self.__dict__[name]

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, adict):
        self.__dict__.update(self.defaults)
        self.update(adict)

    def __getattr__(self, name, default=None):
        try:
            return self.__getitem__(name, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__

    def copy(self):
        return copy.deepcopy(self)

        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad

    def update(self, adict={}):
        for (key, value) in adict.items():
            if key in self.readonly:
                continue
            self.__setitem__(key, value)

    def _pretty_str(self, priorized_keys=[], min_label_length=16):
        keys = list(self.keys())
        try:
            i = max(max([len(k) for k in keys]), min_label_length)
        except ValueError:
            return ""
        pattern = "%%%ds: %%s" % (i)
        other_keys = [k for k in keys if k not in priorized_keys]
        keys = priorized_keys + sorted(other_keys)
        head = [pattern % (k, self.__dict__[k]) for k in keys]
        return "\n".join(head)

    def _cast_type(self, key, value):
        typ = self._types[key]
        new_type = (
            typ[0] if isinstance(typ, collections.abc.Sequence)
            else typ)
        msg = ('Attribute "%s" must be of type %s, not %s. Attempting to '
               'cast %s to %s') % (key, typ, type(value), value, new_type)
        warnings.warn(msg)
        return new_type(value)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def toJSON(self):
        return json.dumps(self.__dict__)


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


class CouchDBSessionMixin:
    base_url = None

    @classmethod
    def _basic_base_url(cls, couchdb_uri):
        proto, user, password, host = re.split("://|:|@", couchdb_uri, maxsplit=3)
        if ':' in host:
            host, port = host.split(":")
        else:
            port = 80
        base_url = f'{proto}://{host}:{port}/'
        auth = dict(user=user, password=password)
        return base_url, auth

    def create_url(self, path):
        return urljoin(self.base_url, path)


class CouchDBSession(CouchDBSessionMixin, requests.Session):
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

    def __init__(self, base_url=None, auth={}, db_name=None):
        self.base_url = base_url
        self.db_name = db_name
        super().__init__()
        self.auth = auth['user'], auth['password']

    def request(self, method, url, *args, **kwargs):
        url = self.create_url(url)
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


class CouchDBSessionAsync(CouchDBSessionMixin, client.ClientSession):
    @classmethod
    def db(cls, couchdb_uri=None, db_name=None):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}/'
        return cls(base_url=base_url, auth=auth, db_name=db_name)

    @classmethod
    def db_design(cls, couchdb_uri=None, db_name=None):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}/_design/{db_name}/'
        return cls(base_url=base_url, auth=auth, db_name=db_name)

    def __init__(self, base_url=None, auth={}, db_name=None):
        self.base_url = base_url
        self.db_name = db_name
        super().__init__(auth=BasicAuth(login=auth['user'], password= auth['password']))

    async def _request(self, method, str_or_url, **kwargs):
        str_or_url = self.create_url(str_or_url)
        response = await super()._request(method, str_or_url, **kwargs)
        if 'ETag' in response.headers: # set couchdb rev in respone
            response.rev = response.headers['ETag'].replace('"','')
        else:
            response.rev = None
        return response

    async def rev(self, str_or_url):
        str_or_url = self.create_url(str_or_url)
        response = await self._request('head', str_or_url)
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

def decode_json(data, child=None):
    data = data if isinstance(data, str) else data.decode('utf8')
    json_data = json.loads(data)
    if child:
        return json_data[child]
    return json_data
    # for debug
    # try:
    #     json_data = json.loads(data)
    #     if child:
    #         return json_data[child]
    #     return json_data
    # except json.decoder.JSONDecodeError:
    #     import ipdb; ipdb.set_trace()

def encode_json(data):
    return json.dumps(data, cls=JSONDefaultDictEncoder)
    # for debug
    # try:
    #     return json.dumps(data, cls=JSONDefaultDictEncoder)
    # except TypeError:
    #     import ipdb; ipdb.set_trace()

def get_rows(response):
    return response.json()['rows']

def get_doc(response):
    data = response.json()
    if 'doc' in data:
        data = data['doc']
    if isinstance(data, dict):
        return AttributeDict(data)
    return data

def get_key(response, key):
    json_data = response.json()[key]
    return json_data
