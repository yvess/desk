"""Tests for the DNS update path.

`Updater._create_diff` turns two versions of a domain document into the
add/update/remove instructions the DNS backend replays against a live zone.
Nothing guarded it before, so these tests pin what it does today, on the real
fixture documents, ahead of the PowerDNS backend swap (M5) -- they have to keep
passing across that swap.
"""
import copy
import json
import logging
import os
import unittest

import httpx

from desk import Worker
from desk.plugin.base import Updater
from desk.plugin.dns.dnsbase import DnsBase
from desk.plugin.dns.powerdns import Powerdns, txt_content, txt_value
from desk.utils import AttributeDict, CouchDBClient, ObjectDict

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def fixture(name):
    with open(os.path.join(FIXTURES, f'couchdb-{name}.json')) as f:
        return json.load(f)


class RecordingDns(DnsBase):
    """A DnsBase that only carries `structure` -- the diff needs nothing else."""

    def set_domain(self, domain):
        pass

    def create(self):
        pass

    def update(self, record=None):
        pass

    def delete(self, record=None):
        pass

    def add_domain(self, domain=None):
        pass

    def del_domain(self, domain=None):
        pass

    def add_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        pass

    def update_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        pass

    def del_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        pass

    def del_records(self, rtype, domain=None):
        pass

    def get_domains(self):
        pass

    def get_records(self, domain=None):
        pass


class DiffFixture:
    """Diffs the `dns-test` fixture against a mutated copy of itself.

    The active (pre-change) document is served the way CouchDB serves it: as the
    attachment named after `active_rev` that the foreman writes when a document
    goes active.
    """

    ACTIVE_REV = '1-active'

    def diff(self, mutate):
        old = fixture('dns-test')
        new = copy.deepcopy(old)
        mutate(new)
        docs = {
            'template-email': fixture('template-dns'),
            'map-ips': fixture('map-ips'),
            f'dns-test/{self.ACTIVE_REV}': old,
        }

        def handler(request):
            key = request.url.path.split('/desk_drawer/', 1)[1]
            return httpx.Response(200, json=docs[key])

        db = CouchDBClient.db(
            'http://cdb:5984', db_name='desk_drawer',
            transport=httpx.MockTransport(handler),
        )
        self.addCleanup(db.close)
        doc = AttributeDict(
            dict(new, state='changed', active_rev=self.ACTIVE_REV)
        )
        return Updater(db, doc, RecordingDns())._create_diff()

    @staticmethod
    def set_ip(doc, host, ip):
        for record in doc['a']:
            if record['host'] == host:
                record['ip'] = ip


class DomainDiffTest(DiffFixture, unittest.TestCase):
    """What the diff does with the record shapes the frontend actually sends."""

    def test_a_changed_value_is_an_update_looked_up_by_key(self):
        diff = self.diff(lambda d: self.set_ip(d, 'www', '172.17.1.21'))

        self.assertEqual(diff['update']['a'], [
            {'host': 'www', 'ip': '172.17.1.21', 'lookup': 'key'},
        ])
        self.assertEqual(diff['append'], {})

    def test_a_changed_key_is_an_update_looked_up_by_value(self):
        diff = self.diff(
            lambda d: d['cname'].__setitem__(0, {'alias': 'weblog', 'host': 'www'})
        )

        self.assertEqual(diff['update']['cname'], [
            {'alias': 'weblog', 'host': 'www', 'lookup': 'value'},
        ])

    def test_a_new_entry_of_an_existing_type_is_appended(self):
        diff = self.diff(
            lambda d: d['a'].append({'host': 'shop', 'ip': '172.17.1.40'})
        )

        self.assertEqual(diff['append']['a'], [
            {'host': 'shop', 'ip': '172.17.1.40'},
        ])
        self.assertEqual(diff['update'], {})

    def test_removing_an_entry_also_reports_the_shifted_tail(self):
        """json_diff compares lists by position, not identity.

        Dropping `blog2` (index 5 of 7) makes every later entry line up against
        its predecessor, so the diff names the *last* entry as removed and the
        rest as updated. The end state is still right: `Powerdns.update` treats
        any rtype in `update` as "delete them all and recreate from the new
        document", which happens after the remove.
        """
        diff = self.diff(
            lambda d: d.__setitem__(
                'a', [a for a in d['a'] if a['host'] != 'blog2']
            )
        )

        self.assertEqual(diff['remove']['a'], [
            {'host': '@', 'ip': '172.17.1.30'},
        ])
        self.assertEqual(
            [entry['lookup'] for entry in diff['update']['a']], ['id']
        )

    def test_emptying_a_type_removes_each_of_its_entries(self):
        diff = self.diff(lambda d: d.__setitem__('cname', []))

        self.assertEqual(diff['remove']['cname'], [
            {'alias': 'blog', 'host': 'www'},
            {'alias': 'new', 'host': 'www'},
        ])


class WholeRecordTypeDiffTest(DiffFixture, unittest.TestCase):
    """A record type appearing or disappearing entirely.

    json_diff reports those at the top level rather than under `_update`, and
    `_create_diff` only read `_update` -- so adding a domain's first TXT record,
    an SPF or DKIM entry, produced an empty diff: the zone was never touched and
    the task was still marked done.
    """

    def test_a_brand_new_record_type_is_appended(self):
        diff = self.diff(
            lambda d: d.__setitem__(
                'txt', [{'name': '@', 'content': 'v=spf1 -all'}]
            )
        )

        self.assertEqual(
            diff['append']['txt'], [{'name': '@', 'content': 'v=spf1 -all'}]
        )

    def test_dropping_a_record_types_key_removes_its_entries(self):
        diff = self.diff(lambda d: d.pop('cname'))

        self.assertEqual(diff['remove']['cname'], [
            {'alias': 'blog', 'host': 'www'},
            {'alias': 'new', 'host': 'www'},
        ])

    def test_the_backend_writes_the_new_type(self):
        """The diff has to reach PowerDNS, not just be computed."""
        diff = self.diff(
            lambda d: d.__setitem__(
                'txt', [{'name': '@', 'content': 'v=spf1 -all'}]
            )
        )
        api = PowerdnsApiStub()
        doc = dict(merged_domain(), txt=[
            {'name': '@', 'content': 'v=spf1 -all'}
        ])
        with api.backend(doc=doc, diff=diff) as pdns:
            pdns.update()

        rrsets = api.sent('PATCH')[0]['rrsets']
        self.assertIn({
            'name': 'test.', 'type': 'TXT', 'ttl': 3600,
            'changetype': 'REPLACE',
            'records': [{'content': '"v=spf1 -all"', 'disabled': False}],
        }, rrsets)
        # SOA and NS ride along on every update; nothing else does
        self.assertEqual({r['type'] for r in rrsets}, {'SOA', 'NS', 'TXT'})


class PowerdnsApiStub:
    """A PowerDNS HTTP API that records what was sent to it.

    `zone` is what a GET of the zone answers, so a REPLACE can be checked
    against records that are already there.
    """

    def __init__(self, zone=None, zones=()):
        self.requests = []
        self.zone = zone or {'rrsets': []}
        self.zones = list(zones)

    def handler(self, request):
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body))
        if request.method == 'GET' and request.url.path.endswith('/zones'):
            return httpx.Response(
                200, json=[{'name': name} for name in self.zones]
            )
        if request.method == 'GET':
            return httpx.Response(200, json=self.zone)
        if request.method == 'POST':
            return httpx.Response(201, json={'name': 'test.'})
        return httpx.Response(204)

    def backend(self, doc=None, diff=None):
        pdns = Powerdns(
            ObjectDict(
                powerdns_api_url='http://ns1:8081', powerdns_api_key='devkey'
            ),
            transport=httpx.MockTransport(self.handler),
        )
        pdns.lookup_map = {
            key.replace('@ip_', '$ip_'): value
            for key, value in fixture('map-ips')['map'].items()
        }
        if doc is not None:
            pdns.set_docs(doc)
        if diff is not None:
            pdns.set_diff(diff)
        return pdns

    def sent(self, method):
        return [body for verb, _, body in self.requests if verb == method]


def merged_domain():
    """The domain document as the worker sees it: fixture + its template.

    The fixtures are pre-migration documents, so the `@ip_` map variables are
    converted the way `to0001` converts them -- a live database has `$ip_`.
    """
    doc = fixture('dns-test')
    doc.update({
        k: v for k, v in fixture('template-dns').items()
        if k not in doc and not k.startswith('_') and k != 'type'
    })
    for record in doc['a']:
        record['ip'] = record['ip'].replace('@ip_', '$ip_')
    return doc


class PowerdnsCreateTest(unittest.TestCase):
    """create() POSTs the whole zone in one request."""

    def setUp(self):
        self.api = PowerdnsApiStub()
        with self.api.backend(doc=merged_domain()) as pdns:
            self.created = pdns.create()
        self.body = self.api.sent('POST')[0]
        self.rrsets = {
            (r['name'], r['type']): [x['content'] for x in r['records']]
            for r in self.body['rrsets']
        }

    def test_it_creates_one_native_zone(self):
        self.assertTrue(self.created)
        self.assertEqual(len(self.api.sent('POST')), 1)
        self.assertEqual(self.body['name'], 'test.')
        self.assertEqual(self.body['kind'], 'Native')

    def test_names_are_absolute(self):
        for name, _ in self.rrsets:
            self.assertTrue(name.endswith('.'), name)

    def test_the_soa_serial_is_left_to_powerdns(self):
        soa = self.rrsets[('test.', 'SOA')][0]

        self.assertEqual(soa.split()[2], '1')

    def test_the_soa_mailbox_is_a_domain_name(self):
        """`dsnmaster@test` in the document is not valid SOA content.

        The API rejects it with 422; the sqlite backend wrote it through and
        PowerDNS served an escaped `dsnmaster\\@test.`
        """
        soa = self.rrsets[('test.', 'SOA')][0]

        self.assertTrue(
            soa.startswith('ns1.localhost. dsnmaster.test. 1 '), soa
        )

    def test_a_records_use_the_host_as_the_name(self):
        self.assertEqual(self.rrsets[('www.test.', 'A')], ['172.17.1.20'])

    def test_the_root_a_record_is_the_zone_apex(self):
        self.assertEqual(self.rrsets[('test.', 'A')], ['172.17.1.30'])

    def test_a_map_variable_is_resolved(self):
        self.assertEqual(self.rrsets[('blog2.test.', 'A')], ['172.17.1.10'])

    def test_cname_targets_are_absolute(self):
        self.assertEqual(self.rrsets[('blog.test.', 'CNAME')], ['www.test.'])

    def test_mx_records_share_the_apex_and_carry_the_priority(self):
        self.assertEqual(
            self.rrsets[('test.', 'MX')], ['10 mx1.test.', '20 mx2.test.']
        )

    def test_nameservers_become_the_ns_rrset(self):
        self.assertEqual(self.rrsets[('test.', 'NS')], ['ns1.localhost.'])


class PowerdnsCreateOnExistingZoneTest(unittest.TestCase):
    """A zone that is already there is patched into shape, not refused.

    PowerDNS answers a second POST of the same zone with 409, so a task retried
    after a partial failure could never succeed otherwise.
    """

    def setUp(self):
        zone = {'rrsets': [
            {'name': 'stale.test.', 'type': 'A', 'ttl': 3600,
             'records': [{'content': '10.0.0.9', 'disabled': False}]},
        ]}
        self.api = PowerdnsApiStub(zone=zone, zones=['test.'])
        with self.api.backend(doc=merged_domain()) as pdns:
            self.created = pdns.create()

    def test_it_patches_instead_of_posting(self):
        self.assertTrue(self.created)
        self.assertEqual(self.api.sent('POST'), [])
        self.assertEqual(len(self.api.sent('PATCH')), 1)

    def test_records_the_document_no_longer_has_are_deleted(self):
        rrsets = self.api.sent('PATCH')[0]['rrsets']

        self.assertIn(
            {'name': 'stale.test.', 'type': 'A', 'changetype': 'DELETE'},
            rrsets,
        )

    def test_the_zones_serial_is_kept(self):
        zone = {'rrsets': [
            {'name': 'test.', 'type': 'SOA', 'ttl': 3600,
             'records': [{'content':
                          'ns1.localhost. dsnmaster.test. 2026090205 '
                          '3600 3600 3600 3600'}]},
        ]}
        api = PowerdnsApiStub(zone=zone, zones=['test.'])
        with api.backend(doc=merged_domain()) as pdns:
            pdns.create()

        soa = [r for r in api.sent('PATCH')[0]['rrsets']
               if r['type'] == 'SOA'][0]
        self.assertEqual(soa['records'][0]['content'].split()[2], '2026090205')


class PowerdnsUpdateTest(unittest.TestCase):
    """update() replaces whole RRsets for the record types the diff touched.

    The SOA and NS RRsets go along every time: the diff only covers the
    record types in `structure`, so a changed refresh, hostmaster, nameserver
    or TTL would otherwise never reach the zone.
    """

    def rrsets_for(self, diff, zone=None, doc=None):
        api = PowerdnsApiStub(zone=zone)
        with api.backend(doc=doc or merged_domain(), diff=diff) as pdns:
            pdns.update()
        self.api = api
        return api.sent('PATCH')[0]['rrsets'] if api.sent('PATCH') else []

    def record_types(self, rrsets):
        return {r['type'] for r in rrsets} - {'SOA', 'NS'}

    def test_it_replaces_every_rrset_of_the_changed_type(self):
        rrsets = self.rrsets_for({
            'update': {'a': [{'host': 'www', 'ip': '172.17.1.21'}]},
            'append': {}, 'remove': {},
        })

        self.assertTrue(all(r['changetype'] == 'REPLACE' for r in rrsets))
        self.assertEqual(self.record_types(rrsets), {'A'})

    def test_it_leaves_untouched_types_alone(self):
        rrsets = self.rrsets_for({
            'update': {}, 'remove': {},
            'append': {'cname': [{'alias': 'shop', 'host': 'www'}]},
        })

        self.assertEqual(self.record_types(rrsets), {'CNAME'})

    def test_it_reads_the_zone_once(self):
        self.rrsets_for({
            'update': {'a': [{'host': 'www', 'ip': '172.17.1.21'}]},
            'append': {'cname': [{'alias': 'shop', 'host': 'www'}]},
            'remove': {'txt': [{'name': '@', 'content': 'x'}]},
        })

        self.assertEqual(
            [verb for verb, _, _ in self.api.requests], ['GET', 'PATCH']
        )

    def test_a_name_the_type_no_longer_covers_is_deleted(self):
        """REPLACE only reaches names the document still has."""
        zone = {'rrsets': [
            {'name': 'gone.test.', 'type': 'A', 'ttl': 3600,
             'records': [{'content': '10.0.0.9', 'disabled': False}]},
        ]}
        rrsets = self.rrsets_for(
            {'update': {'a': []}, 'append': {}, 'remove': {}}, zone=zone
        )

        deleted = [r for r in rrsets if r['changetype'] == 'DELETE']
        self.assertEqual(
            deleted, [{'name': 'gone.test.', 'type': 'A',
                       'changetype': 'DELETE'}]
        )

    def test_a_changed_soa_field_reaches_the_zone(self):
        """The old backend rewrote the SOA from the document on every update;
        the diff never carries soa_* fields, so this has to be unconditional.
        """
        doc = merged_domain()
        doc['soa_refresh'] = 7200
        rrsets = self.rrsets_for(
            {'update': {}, 'append': {}, 'remove': {}}, doc=doc
        )

        soa = [r for r in rrsets if r['type'] == 'SOA'][0]
        self.assertEqual(soa['changetype'], 'REPLACE')
        self.assertEqual(
            soa['records'][0]['content'].split()[3:], ['7200'] + ['3600'] * 3
        )

    def test_changed_nameservers_reach_the_zone(self):
        doc = merged_domain()
        doc['nameservers'] = ['ns1.localhost', 'ns2.localhost']
        rrsets = self.rrsets_for(
            {'update': {}, 'append': {}, 'remove': {}}, doc=doc
        )

        ns = [r for r in rrsets if r['type'] == 'NS'][0]
        self.assertEqual(
            [x['content'] for x in ns['records']],
            ['ns1.localhost.', 'ns2.localhost.'],
        )

    def test_the_current_serial_is_handed_back_for_powerdns_to_bump(self):
        """DEFAULT soa-edit-api bumps what it is given; handing it `1` would
        restart the serial at today's 01, below what secondaries have seen.
        """
        zone = {'rrsets': [
            {'name': 'test.', 'type': 'SOA', 'ttl': 3600,
             'records': [{'content':
                          'ns1.localhost. dsnmaster.test. 2026090205 '
                          '3600 3600 3600 3600'}]},
        ]}
        rrsets = self.rrsets_for(
            {'update': {}, 'append': {}, 'remove': {}}, zone=zone
        )

        soa = [r for r in rrsets if r['type'] == 'SOA'][0]
        self.assertEqual(soa['records'][0]['content'].split()[2], '2026090205')

    def test_without_a_diff_it_does_nothing(self):
        api = PowerdnsApiStub()
        with api.backend(doc=merged_domain()) as pdns:
            self.assertFalse(pdns.update())
        self.assertEqual(api.requests, [])


class TxtContentTest(unittest.TestCase):
    """TXT content is quoted master-file syntax: escapes and 255-byte strings."""

    def test_quotes_and_backslashes_are_escaped(self):
        self.assertEqual(
            txt_content('say "hi" c:\\temp'), '"say \\"hi\\" c:\\\\temp"'
        )

    def test_a_long_value_is_split_into_255_byte_strings(self):
        """A DKIM key does not fit one <character-string>."""
        content = txt_content('k' * 300)

        strings = content.split('" "')
        self.assertEqual([len(x.strip('"')) for x in strings], [255, 45])

    def test_an_empty_value_is_one_empty_string(self):
        self.assertEqual(txt_content(''), '""')

    def test_the_export_reverses_it(self):
        for value in ('v=spf1 -all', 'say "hi" c:\\temp', 'k' * 300, ''):
            self.assertEqual(txt_value(txt_content(value)), value)

    def test_the_backend_writes_the_escaped_form(self):
        doc = merged_domain()
        doc['txt'] = [{'name': '@', 'content': 'o\'brien says "hi"'}]
        api = PowerdnsApiStub()
        with api.backend(doc=doc) as pdns:
            pdns.create()

        txt = [r for r in api.sent('POST')[0]['rrsets']
               if r['type'] == 'TXT'][0]
        self.assertEqual(
            txt['records'][0]['content'], '"o\'brien says \\"hi\\""'
        )


class PowerdnsZoneTest(unittest.TestCase):
    def test_delete_removes_the_zone(self):
        api = PowerdnsApiStub()
        with api.backend(doc=merged_domain()) as pdns:
            self.assertTrue(pdns.delete())

        self.assertEqual(
            [(verb, path) for verb, path, _ in api.requests],
            [('DELETE', '/api/v1/servers/localhost/zones/test.')],
        )

    def test_get_domains_strips_the_root_dot(self):
        api = PowerdnsApiStub(zones=['test.'])
        with api.backend() as pdns:
            self.assertEqual(pdns.get_domains(), ['test'])

    def test_an_error_status_raises(self):
        """The sqlite backend logged failures and carried on."""
        def failing(request):
            return httpx.Response(422, json={'error': 'bad record'})

        pdns = Powerdns(
            ObjectDict(
                powerdns_api_url='http://ns1:8081', powerdns_api_key='devkey'
            ),
            transport=httpx.MockTransport(failing),
        )
        pdns.set_docs(merged_domain())
        pdns.lookup_map = {'$ip_web1': '172.17.1.10'}
        with pdns, self.assertRaises(httpx.HTTPStatusError):
            pdns.create()

    def test_the_api_key_is_sent(self):
        api = PowerdnsApiStub()
        with api.backend() as pdns:
            self.assertEqual(pdns.api.headers['X-API-Key'], 'devkey')


class PowerdnsExportTest(unittest.TestCase):
    """get_records feeds dns-export-powerdns, so its shape has to stay put."""

    def records(self):
        zone = {'rrsets': [
            {'name': 'test.', 'type': 'SOA', 'ttl': 3600,
             'records': [{'content': 'ns1.localhost. hm.test. 1 1 1 1 1'}]},
            {'name': 'test.', 'type': 'NS', 'ttl': 3600,
             'records': [{'content': 'ns1.localhost.'}]},
            {'name': 'www.test.', 'type': 'A', 'ttl': 3600,
             'records': [{'content': '172.17.1.20'}]},
            {'name': 'test.', 'type': 'MX', 'ttl': 3600,
             'records': [{'content': '10 mx1.test.'},
                         {'content': '20 mx2.test.'}]},
            {'name': 'blog.test.', 'type': 'CNAME', 'ttl': 3600,
             'records': [{'content': 'www.test.'}]},
            {'name': 'test.', 'type': 'TXT', 'ttl': 3600,
             'records': [{'content': '"v=spf1 -all"'},
                         {'content': '"p=abc" "def"'}]},
        ]}
        api = PowerdnsApiStub(zone=zone)
        with api.backend() as pdns:
            return pdns.get_records('test')

    def test_the_soa_is_not_exported(self):
        self.assertNotIn('soa', self.records())

    def test_names_come_back_relative_to_the_zone(self):
        records = self.records()

        self.assertEqual(records['a'], [('www', '172.17.1.20')])
        self.assertEqual(records['cname'], [('blog', 'www')])

    def test_mx_priority_is_not_part_of_the_exported_value(self):
        self.assertEqual(
            self.records()['mx'], [('@', 'mx1'), ('@', 'mx2')]
        )

    def test_txt_content_is_unquoted(self):
        """The trailing dot is what the sqlite backend produced too.

        `reverse_fqdn` is applied to every value type except A/AAAA, and on a
        TXT body it just appends a dot. Kept as it was so the export of a zone
        can be diffed across the backend swap; it only affects this text dump,
        not what is served.
        """
        self.assertEqual(
            self.records()['txt'], [('@', 'p=abcdef.'), ('@', 'v=spf1 -all.')]
        )


class WorkerBackendFailureTest(unittest.TestCase):
    """A rejected DNS change fails the task; it does not kill the worker.

    The sqlite backend logged every failure and returned normally, so a task
    was marked `done` whether or not the zone had been written. The API backend
    raises instead -- which, unguarded, escapes through the `_changes` queue
    coroutine and stops the worker processing anything further.
    """

    def test_an_unreachable_backend_marks_the_task_failed(self):
        def couch(request):
            return httpx.Response(200, json={
                '_id': 'map-ips', 'map': {'$ip_web1': '172.17.1.10'},
            })

        worker = object.__new__(Worker)
        worker.logger = logging.getLogger('desk.test')
        worker.provides = {'domain': [{'backend': 'powerdns', 'name': 'ns1'}]}
        worker.db = CouchDBClient.db(
            'http://cdb:5984', db_name='desk_drawer',
            transport=httpx.MockTransport(couch),
        )
        self.addCleanup(worker.db.close)
        # port 9 is discard: nothing listens, so the API call cannot connect
        worker.settings = ObjectDict(
            powerdns_api_url='http://127.0.0.1:9', powerdns_api_key='devkey'
        )
        doc = AttributeDict(dict(merged_domain(), state='new', type='domain'))

        with self.assertLogs('desk.test', level='ERROR') as logged:
            failed = worker._do_task(doc)

        self.assertFalse(failed)
        self.assertIn('task failed on', logged.output[0])


if __name__ == '__main__':
    unittest.main()
