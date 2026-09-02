from datetime import date
import calendar
import json
import httpx
import collections
from json import JSONEncoder
from importlib import import_module


class ObjectDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

class JSONDefaultDictEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

# based on obspy's AttributeDict, trimmed to what this codebase uses: documents
# come out of CouchDB as nested dicts and are read as `doc.a[0].host`
class AttributeDict(collections.abc.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.update(dict(*args, **kwargs))

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    def __getitem__(self, name, default=None):
        try:
            return self.__dict__[name]
        except KeyError:
            if default is None:
                raise
            return default

    def __setitem__(self, key, value):
        if (isinstance(value, collections.abc.Mapping)
                and not isinstance(value, AttributeDict)):
            value = AttributeDict(value)
        self.__dict__[key] = value

    def __delitem__(self, name):
        del self.__dict__[name]

    def __getattr__(self, name, default=None):
        try:
            return self.__getitem__(name, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__

    def update(self, adict={}):
        for (key, value) in adict.items():
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


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


# couchdb expects these view parameters as JSON, not as plain strings
VIEW_JSON_PARAMS = ('key', 'keys', 'startkey', 'endkey')


def encode_view_params(params):
    return {
        name: json.dumps(value)
        if name in VIEW_JSON_PARAMS or isinstance(value, bool) else value
        for name, value in params.items()
    }


class CouchDBClientMixin:
    base_url = None
    db_name = None

    @classmethod
    def _basic_base_url(cls, couchdb_uri):
        url = httpx.URL(couchdb_uri)
        base_url = f'{url.scheme}://{url.host}'
        if url.port:
            base_url = f'{base_url}:{url.port}'
        auth = (url.username, url.password) if url.username else None
        return base_url, auth

    @classmethod
    def db(cls, couchdb_uri=None, db_name=None, **kwargs):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}'
        client = cls(base_url=base_url, auth=auth, **kwargs)
        client.db_name = db_name
        return client

    @classmethod
    def db_design(cls, couchdb_uri=None, db_name=None, **kwargs):
        base_url, auth = cls._basic_base_url(couchdb_uri)
        base_url = f'{base_url}/{db_name}/_design/{db_name}'
        client = cls(base_url=base_url, auth=auth, **kwargs)
        client.db_name = db_name
        return client

def response_add_rev(response):
    etag = response.headers.get('ETag')
    if etag: # set couchdb rev in response, ETag may be weakened (W/) by proxies
        response.rev = etag.removeprefix('W/').strip('"')
    else:
        response.rev = None
    return response

# rev is attached in send() so that request(), stream() and the
# convenience methods all pass through the same seam
class CouchDBClient(httpx.Client, CouchDBClientMixin):
    def send(self, *args, **kwargs):
        response = super().send(*args, **kwargs)
        return response_add_rev(response)

    def rev(self, *args, **kwargs):
        response = self.head(*args, **kwargs)
        return response.rev

    def view(self, name, ddoc=None, **params):
        """GET {db}/_design/{ddoc}/_view/{name}, returns the view rows.

        ddoc defaults to the design doc named after the database, the only one
        this project installs (see desk/_design/).
        """
        response = self.get(
            f'_design/{ddoc or self.db_name}/_view/{name}',
            params=encode_view_params(params)
        )
        response.raise_for_status()
        return get_rows(response)


class CouchDBClientAsync(httpx.AsyncClient, CouchDBClientMixin):
    async def send(self, *args, **kwargs):
        response = await super().send(*args, **kwargs)
        return response_add_rev(response)

    async def rev(self, *args, **kwargs):
        response = await self.head(*args, **kwargs)
        return response.rev


def parse_date(date_string, force_day=None):
    year, month, day = [int(item) for item in date_string.split("-")]
    if force_day == 'start':
        day = 1
    elif force_day == 'end':
        day = calendar.monthrange(year, month)[1]
    elif force_day is not None:
        raise ValueError(f"unknown force_day value: {force_day!r}")
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
    if getattr(settings, 'worker_extcrm', None):
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

def encode_json(data):
    return json.dumps(data, cls=JSONDefaultDictEncoder)

def get_rows(response):
    try:
        return response.json()['rows']
    except (ValueError, KeyError, TypeError):
        return None

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
