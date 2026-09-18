"""Tests for the command layer ported off couchdbkit in M2.

Every command below used to call `Server(...)` / `db.view(...)` and crashed on
import or first use. The tests drive them through a real `CouchDBClient` whose
only stub is the HTTP transport, so the view URLs and the JSON that comes back
are the ones CouchDB would see.
"""
import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

import httpx

from desk.command import FileDesignDocsLoader, InstallDbCommand
from desk.command import InstallWorkerCommand, MigrateCommand
from desk.plugin.base import MergedDoc
from desk.plugin.dns.cmd_powerdns import DnsCheckCommand
from desk.plugin.dns.cmd_powerdns import PowerdnsRebuildCommand
from desk.plugin.dns.powerdns import Powerdns
from desk.plugin.invoice.cmd import CreateInvoicesCommand
from desk.plugin.invoice.invoice import Invoice
from desk.plugin.service.query import QueryServices
from desk.utils import CouchDBClient

VIEW_PREFIX = '/desk_drawer/_design/desk_drawer/_view/'


def view_name(request):
    """The view a request asks for, or None for a plain document request."""
    path = request.url.path
    return path[len(VIEW_PREFIX):] if path.startswith(VIEW_PREFIX) else None


def doc_id(request):
    return request.url.path.rsplit('/', 1)[-1]


class CouchStub:
    """Serves view rows and documents over httpx.MockTransport."""

    def __init__(self, views=None, docs=None, failing=None):
        self.views = views or {}
        self.docs = docs or {}
        # doc id -> status: CouchDB answers e.g. 500 for that document
        self.failing = failing or {}
        self.requests = []

    def handler(self, request):
        self.requests.append(request)
        name = view_name(request)
        if name is not None:
            return httpx.Response(200, json={'rows': self.views[name]})
        if request.method == 'PUT':
            return httpx.Response(
                201, json={'ok': True}, headers={'ETag': '"2-new"'}
            )
        if doc_id(request) in self.failing:
            status = self.failing[doc_id(request)]
            return httpx.Response(status, json={'error': f'http {status}'})
        if doc_id(request) not in self.docs:
            return httpx.Response(
                404, json={'error': 'not_found', 'reason': 'missing'}
            )
        return httpx.Response(200, json=self.docs[doc_id(request)])

    def client(self):
        return CouchDBClient.db(
            'http://cdb:5984', db_name='desk_drawer',
            transport=httpx.MockTransport(self.handler),
        )

    def written(self, method='PUT'):
        return [
            json.loads(r.content) for r in self.requests if r.method == method
        ]


SERVICE_DEFINITION = {
    '_id': 'servicedefinition-hosting',
    'type': 'service_definition',
    'service_type': 'hosting',
    'title': 'Hosting',
    'packages': {'basic': {'title': 'Basic', 'price': '10.00', 'included': {}}},
    'addons': {},
}

SERVICE_TEMPLATE = {
    '_id': 'template-hosting',
    'type': 'template',
    'template_type': 'service',
    'service_type': 'hosting',
    'package_type': 'basic',
}


def settings(**overrides):
    """Settings as worker.py hands them over: an argparse namespace."""
    values = {'couchdb_uri': 'http://cdb:5984', 'couchdb_db': 'desk_drawer'}
    values.update(overrides)
    return argparse.Namespace(**values)


class CreateInvoicesCommandTestCase(unittest.TestCase):
    """invoices-create — the core billing path."""

    def setUp(self):
        Invoice.service_definitons = {}
        MergedDoc.cache = {}
        self.addCleanup(setattr, Invoice, 'service_definitons', {})
        self.couch = CouchStub(
            views={
                'client_is_billable': [{
                    'id': 'client-1', 'key': 'client-1',
                    'doc': {
                        '_id': 'client-1', 'type': 'client',
                        'name': 'Muster AG', 'extcrm_id': 'p1',
                    },
                }],
                'service_definition': [{
                    'id': SERVICE_DEFINITION['_id'],
                    'doc': SERVICE_DEFINITION,
                }],
                # the service doc only carries what differs from its template
                'service_by_client': [{
                    'id': 'service-1',
                    'doc': {
                        '_id': 'service-1', 'type': 'service',
                        'client_id': 'client-1',
                        'template_id': SERVICE_TEMPLATE['_id'],
                    },
                }],
            },
            docs={SERVICE_TEMPLATE['_id']: SERVICE_TEMPLATE},
        )
        self.command = CreateInvoicesCommand()
        self.command.set_settings(settings(
            invoice_nr=100, year=2026,
            invoice_date='2026-12-31', invoice_tax='0.0',
            invoice_template_dir='.', invoice_output_dir='.',
            limit_client_id=None, max=0,
        ))
        self.command.db.close()
        self.command.db = self.couch.client()
        self.addCleanup(self.command.db.close)

    def run_command(self):
        # autospec keeps the bound instance, so the rendered invoice is readable
        with patch.object(Invoice, 'render_pdf', autospec=True) as render_pdf:
            with redirect_stdout(io.StringIO()) as out:
                self.command.run()
        self.invoices = [call.args[0] for call in render_pdf.call_args_list]
        return render_pdf, out.getvalue()

    def test_a_billable_client_gets_an_invoice(self):
        render_pdf, out = self.run_command()
        self.assertEqual(render_pdf.call_count, 1)
        self.assertIn('total 120.0', out)

    def test_the_views_it_reads(self):
        self.run_command()
        self.assertEqual(
            [view_name(r) for r in self.couch.requests if view_name(r)],
            ['client_is_billable', 'service_definition', 'service_by_client'],
        )

    def test_service_definitions_are_loaded_once(self):
        self.run_command()
        self.assertEqual(
            Invoice.service_definitons['hosting'], SERVICE_DEFINITION
        )

    def test_a_templated_service_doc_is_merged_before_billing(self):
        """The view returns plain dicts; MergedDoc reads doc.template_id."""
        self.run_command()
        doc = self.invoices[0].doc
        service = doc['services']['hosting']['items'][0]
        self.assertEqual(service['package_title'], 'Basic')
        self.assertEqual(service['price'], 10.0)
        self.assertEqual(service['months'], 12)
        self.assertEqual(doc['amount'], 120.0)

    def test_the_year_setting_decides_the_billed_period(self):
        """--year was parsed and then ignored: the cycle always took today's."""
        self.command.settings.year = 2024
        self.run_command()
        service = self.invoices[0].doc['services']['hosting']['items'][0]
        self.assertEqual(service['start_date'], date(2024, 1, 1))
        self.assertEqual(service['end_date'], date(2024, 12, 31))

    def test_limit_client_id_skips_other_clients(self):
        self.command.settings.limit_client_id = 'client-2'
        render_pdf, _ = self.run_command()
        self.assertEqual(render_pdf.call_count, 0)

    def test_an_empty_price_on_a_templated_service_falls_back(self):
        """MergedDoc turns price '' into [] when the template has no price."""
        self.couch.views['service_by_client'][0]['doc']['price'] = ''
        self.run_command()
        service = self.invoices[0].doc['services']['hosting']['items'][0]
        self.assertEqual(service['price'], 10.0)
        self.assertFalse(service['price_overwritten'])

    def test_the_invoice_files_are_named_after_the_client(self):
        """client_name_normalized() returned bytes and crashed on replace()."""
        self.couch.views['client_is_billable'][0]['doc']['name'] = 'Müller AG'
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'invoice_tpl.html'), 'w') as tpl:
                tpl.write('{{ client_name }} {{ total }}')
            self.command.settings.invoice_template_dir = tmp
            self.command.settings.invoice_output_dir = tmp
            # weasyprint is the boundary here: the html is written by desk,
            # the pdf by weasyprint
            with patch('desk.plugin.invoice.invoice.HTML') as html:
                with redirect_stdout(io.StringIO()):
                    self.command.run()
            written = os.listdir(os.path.join(tmp, 'html'))
        self.assertEqual(
            written, ['2026-12-31_CHF120.00_Nr100_hosting-muller-ag_ta.html']
        )
        self.assertEqual(html.return_value.write_pdf.call_count, 1)


class MigrateCommandTestCase(unittest.TestCase):
    """migrate — `db` was an undefined name and db.get returned a response."""

    def setUp(self):
        self.old_domain = {
            '_id': 'domain-test-ch', '_rev': '1-old', 'type': 'domain',
            'version': 0, 'state': 'active', 'active_rev': '1-old',
            'a': [{'host': 'www', 'ip': '@ip_web'}],
            'txt': [{'name': '@', 'txt': 'v=spf1 -all'}],
        }
        self.couch = CouchStub(
            views={'version': [{
                'id': 'domain-test-ch', 'key': 0, 'value': 'domain',
            }]},
            docs={'domain-test-ch': self.old_domain},
        )
        self.command = MigrateCommand()
        self.command.set_settings(settings())
        self.command.db.close()
        self.command.db = self.couch.client()
        self.addCleanup(self.command.db.close)
        with redirect_stdout(io.StringIO()):
            self.command.run()

    def test_the_migration_writes_the_document_back(self):
        self.assertEqual(len(self.couch.written()), 1)
        self.assertEqual(self.couch.written()[0]['version'], 1)

    def test_to0001_converted_the_document(self):
        migrated = self.couch.written()[0]
        self.assertEqual(migrated['a'][0]['ip'], '$ip_web')
        self.assertEqual(migrated['txt'][0]['content'], 'v=spf1 -all')
        self.assertNotIn('active_rev', migrated)

    def test_the_migration_leaves_the_document_state_alone(self):
        """A migration must not queue every domain for reprocessing.

        to0001 used to force state='new'. Once the `version` view was fixed to
        index version-less documents, that turned `dworker migrate` into a
        rebuild of every zone in the database.
        """
        self.assertEqual(self.couch.written()[0]['state'], 'active')

    def test_it_stops_when_no_further_migration_exists(self):
        # to0002 does not exist, so version 1 is the end of the chain
        self.assertEqual(len(self.couch.written()), 1)


class PowerdnsApiStub:
    """A PowerDNS HTTP API over httpx.MockTransport, recording what it is sent."""

    def __init__(self, zones=()):
        self.zones = list(zones)
        self.requests = []

    def handler(self, request):
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body))
        if request.method == 'GET' and request.url.path.endswith('/zones'):
            return httpx.Response(
                200, json=[{'name': name} for name in self.zones]
            )
        if request.method == 'GET':
            return httpx.Response(200, json={'rrsets': []})
        if request.method == 'POST':
            return httpx.Response(201, json={'name': 'test.ch.'})
        return httpx.Response(204)

    def backend(self, settings):
        return Powerdns(settings, transport=httpx.MockTransport(self.handler))

    def methods(self):
        return [method for method, _, _ in self.requests]

    def sent(self, method):
        return [body for verb, _, body in self.requests if verb == method]


class PowerdnsRebuildCommandTestCase(unittest.TestCase):
    """dns-rebuild-powerdns — `db.view(...).one()` no longer exists."""

    def setUp(self):
        MergedDoc.cache = {}
        self.couch = CouchStub(
            views={'domain_by_name': [{
                'id': 'domain-test-ch', 'key': 'test.ch',
                'doc': {
                    '_id': 'domain-test-ch', 'type': 'domain',
                    'template_id': 'template-domain',
                    'domain': 'test.ch',
                },
            }]},
            docs={
                'map-ips': {'_id': 'map-ips', 'map': {'$ip_web': '1.2.3.4'}},
                'template-domain': {
                    '_id': 'template-domain', 'type': 'template',
                    'nameservers': ['ns1.test.ch'],
                    'soa_primary': 'ns1.test.ch',
                    'soa_hostmaster': 'hostmaster@test.ch',
                    'soa_refresh': 3600, 'soa_retry': 3600,
                    'soa_expire': 3600, 'soa_default_ttl': 3600,
                    'a': [{'host': 'www', 'ip': '$ip_web'}],
                },
            },
        )
        self.pdns_api = PowerdnsApiStub()
        self.command = PowerdnsRebuildCommand()
        self.command.set_settings(settings(
            powerdns_api_url='http://ns1:8081', powerdns_api_key='devkey',
            target=None, only_delete=False,
        ))
        self.command.db.close()
        self.command.db = self.couch.client()
        self.addCleanup(self.command.db.close)

    def rebuild(self, domain):
        """`_rebuild` as `run` calls it: backend built, lookup map set."""
        self.command.pdns = self.pdns_api.backend(self.command.settings)
        self.addCleanup(self.command.pdns.api.close)
        self.command.pdns.set_lookup_map(self.couch.docs['map-ips'])
        self.command._rebuild(domain)

    def rrsets(self, method):
        return {
            (rrset['name'], rrset['type']): [
                record['content'] for record in rrset['records']
            ]
            for rrset in self.pdns_api.sent(method)[0]['rrsets']
        }

    def test_rebuild_merges_the_domain_with_its_template(self):
        self.rebuild('test.ch')

        rrsets = self.rrsets('POST')
        self.assertEqual(rrsets[('test.ch.', 'NS')], ['ns1.test.ch.'])
        self.assertEqual(rrsets[('www.test.ch.', 'A')], ['1.2.3.4'])

    def test_rebuild_syncs_the_zone(self):
        """CouchDB is authoritative, so the zone is made to match it.

        It used to delete the zone and recreate it, carrying the old SOA serial
        across by hand; the API bumps the serial itself, and patching an
        existing zone keeps that serial climbing.
        """
        self.pdns_api.zones = ['test.ch.']

        self.rebuild('test.ch')

        self.assertEqual(self.pdns_api.methods(), ['GET', 'GET', 'PATCH'])
        self.assertEqual(
            self.rrsets('PATCH')[('www.test.ch.', 'A')], ['1.2.3.4']
        )

    def run_command(self):
        # run() builds its own backend; hand it the real one over the stub API
        with patch(
            'desk.plugin.dns.cmd_powerdns.Powerdns', self.pdns_api.backend,
        ):
            with redirect_stdout(io.StringIO()):
                with patch('builtins.input', return_value='no'):
                    self.command.run()
        self.addCleanup(self.command.pdns.api.close)

    def test_the_lookup_map_is_read_as_a_document(self):
        self.run_command()
        self.assertEqual(self.command.pdns.lookup_map, {'$ip_web': '1.2.3.4'})

    def test_a_missing_lookup_map_aborts_the_run(self):
        """A rebuild without the map would fail on the first `$ip_` value."""
        del self.couch.docs['map-ips']
        with self.assertRaises(LookupError) as raised:
            self.run_command()
        self.assertIn('map-ips', str(raised.exception))
        self.assertEqual(self.pdns_api.requests, [])

    def test_a_failing_couchdb_aborts_the_run(self):
        self.couch.failing['map-ips'] = 500
        with self.assertRaises(httpx.HTTPStatusError):
            self.run_command()

    def test_rebuild_of_an_unknown_domain_names_it(self):
        """An empty view result used to raise a bare IndexError."""
        self.couch.views['domain_by_name'] = []
        with self.assertRaises(LookupError) as raised:
            self.rebuild('nosuch.ch')
        self.assertIn('nosuch.ch', str(raised.exception))
        self.assertEqual(self.pdns_api.requests, [])


class QueryServicesTestCase(unittest.TestCase):
    """service-query — `Server` was undefined."""

    def query(self, extra_rows=(), **overrides):
        rows = [{
            'id': 'service-1', 'key': ['hosting', 'basic'],
            'doc': {
                '_id': 'service-1', 'extcrm_id': 'c1-p2',
                'is_billable': True,
            },
            'value': {'included_service_items': [{'itemid': 'domain'}]},
        }] + list(extra_rows)
        couch = CouchStub(
            views={'service_type': rows, 'service_package_addon': rows}
        )
        options = dict(
            service='hosting', service_packages=None, service_addons=None,
            only_billable=False,
        )
        options.update(overrides)
        with couch.client() as db:
            services = QueryServices(settings(**options), db)
            with redirect_stdout(io.StringIO()) as out:
                services.query()
        return couch, out.getvalue()

    def test_it_reads_the_service_type_view(self):
        couch, _ = self.query()
        request = couch.requests[0]
        self.assertEqual(view_name(request), 'service_type')
        self.assertEqual(request.url.params['startkey'], '["hosting"]')

    def test_it_prints_one_line_per_service(self):
        _, out = self.query()
        # the Dummy crm has no contacts, so the placeholder columns are used
        self.assertIn('# No Email #;# no contact#;hosting-basic;domain', out)
        self.assertIn('total: 1', out)

    def test_a_package_narrows_the_view(self):
        couch, _ = self.query(service_packages='basic')
        self.assertEqual(view_name(couch.requests[0]), 'service_package_addon')

    def test_a_service_of_a_deleted_client_is_reported_not_fatal(self):
        """The view links the client doc, which is null once the client is
        deleted; that row used to raise TypeError and abort the listing."""
        orphan = {
            'id': 'service-2', 'key': ['hosting', 'basic'], 'doc': None,
            'value': {'_id': 'client-gone'},
        }
        _, out = self.query(extra_rows=[orphan])
        self.assertIn('*** no extcrm_id', out)
        self.assertIn('total: 1', out)


class StubValidator:
    """Records how dns-check builds its validators; answers as told."""

    map_doc_id = 'map-ips'
    built = []
    valid = {}

    def __init__(self, doc, lookup=None, lookup_map=None):
        self.doc = doc
        self.lookup = lookup
        self.lookup_map = lookup_map
        StubValidator.built.append(self)

    def do_check(self):
        return StubValidator.valid.get(self.doc['domain'], True)


class DnsCheckCommandTestCase(unittest.TestCase):
    """dns-check — one validator per domain, exit status from the result."""

    def setUp(self):
        MergedDoc.cache = {}
        StubValidator.built = []
        StubValidator.valid = {}
        self.couch = CouchStub(
            views={'domain_by_name': [
                {'id': 'domain-a', 'key': 'a.ch', 'doc': {
                    '_id': 'domain-a', 'type': 'domain', 'domain': 'a.ch',
                    'nameservers': ['ns1.a.ch'],
                }},
                {'id': 'domain-b', 'key': 'b.ch', 'doc': {
                    '_id': 'domain-b', 'type': 'domain', 'domain': 'b.ch',
                    'nameservers': ['ns1.b.ch'],
                }},
            ]},
            docs={
                'map-ips': {'_id': 'map-ips', 'map': {'$ip_web': '1.2.3.4'}},
            },
        )
        self.command = DnsCheckCommand()

    def run_command(self, target=None, nameservers=()):
        self.command.set_settings(
            settings(target=target, nameservers=list(nameservers))
        )
        self.command.db.close()
        self.command.db = self.couch.client()
        self.addCleanup(self.command.db.close)
        self.output = io.StringIO()
        with patch('desk.plugin.dns.cmd_powerdns.DnsValidator', StubValidator):
            with redirect_stdout(self.output):
                return self.command.run()

    def test_the_parser_collects_nameserver_overrides(self):
        parser = argparse.ArgumentParser()
        self.command.setup_parser(
            parser.add_subparsers(dest='command'),
            {'args': ['-c'], 'kwargs': {'dest': 'config'}},
        )
        args = parser.parse_args(
            ['dns-check', 'a.ch', '-n', 'ns1.a.ch=127.0.0.1',
             '-n', 'ns2.a.ch=127.0.0.2']
        )

        self.assertEqual(args.target, 'a.ch')
        self.assertEqual(
            args.nameservers, ['ns1.a.ch=127.0.0.1', 'ns2.a.ch=127.0.0.2']
        )

    def test_every_domain_is_checked_when_no_target_is_given(self):
        """The stub view ignores `key`, so both lookups answer a.ch; what is
        pinned is one validator per listed domain and the summary line.
        """
        self.assertTrue(self.run_command())

        self.assertEqual(len(StubValidator.built), 2)
        self.assertIn('2/2 zones match', self.output.getvalue())

    def test_a_failing_zone_makes_the_run_report_false(self):
        """worker.py turns the False into exit status 1."""
        StubValidator.valid = {'a.ch': False}

        self.assertFalse(self.run_command(target='a.ch'))
        self.assertIn('FAIL a.ch', self.output.getvalue())
        self.assertIn('0/1 zones match', self.output.getvalue())

    def test_nameserver_overrides_are_split_and_the_map_is_read(self):
        self.run_command(target='a.ch', nameservers=['ns1.a.ch=127.0.0.1'])

        validator, = StubValidator.built
        self.assertEqual(validator.lookup, {'ns1.a.ch': '127.0.0.1'})
        self.assertEqual(validator.lookup_map, {'$ip_web': '1.2.3.4'})

    def test_a_missing_map_doc_is_tolerated(self):
        del self.couch.docs['map-ips']
        self.run_command(target='a.ch')

        self.assertEqual(StubValidator.built[0].lookup_map, {})

    def test_an_unknown_target_names_it(self):
        self.couch.views['domain_by_name'] = []
        with self.assertRaises(LookupError) as raised:
            self.run_command(target='nope.ch')
        self.assertIn('nope.ch', str(raised.exception))


class InstallDbCommandTest(unittest.TestCase):
    """install-db has to create the database before writing the design doc."""

    def setUp(self):
        self.requests = []
        self.existing_dbs = set()

    def handler(self, request):
        self.requests.append(request)
        is_db_itself = request.url.path.rstrip('/') == '/desk_drawer'
        if request.method == 'HEAD':
            found = 'desk_drawer' in self.existing_dbs if is_db_itself else False
            return httpx.Response(200 if found else 404)
        if is_db_itself:  # PUT /desk_drawer -- create the database
            self.existing_dbs.add('desk_drawer')
            return httpx.Response(201, json={'ok': True})
        if 'desk_drawer' not in self.existing_dbs:
            return httpx.Response(404, json={'error': 'not_found'})
        return httpx.Response(201, json={'ok': True})

    def run_command(self):
        command = InstallDbCommand()
        command.set_settings({
            'couchdb_uri': 'http://cdb:5984', 'couchdb_db': 'desk_drawer',
        })
        command.db.close()
        command.db = CouchDBClient.db(
            'http://cdb:5984', db_name='desk_drawer',
            transport=httpx.MockTransport(self.handler),
        )
        self.addCleanup(command.db.close)
        # FileDesignDocsLoader reads desk/_design/desk_drawer/ relative to cwd
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        command.run()
        return [(r.method, r.url.path) for r in self.requests]

    def test_creates_the_database_on_a_fresh_server(self):
        calls = self.run_command()

        self.assertIn(('PUT', '/desk_drawer/'), calls)
        self.assertIn(
            ('PUT', '/desk_drawer/_design/desk_drawer/'), calls
        )

    def test_leaves_an_existing_database_alone(self):
        self.existing_dbs.add('desk_drawer')

        calls = self.run_command()

        self.assertNotIn(('PUT', '/desk_drawer/'), calls)
        self.assertIn(
            ('PUT', '/desk_drawer/_design/desk_drawer/'), calls
        )


class InstallWorkerCommandTest(unittest.TestCase):
    """run() uses the client set_settings built, it does not rebuild one.

    Both install commands used to re-run `set_settings(self.settings)` inside
    `run()`, which replaced `self.db` with a fresh client against the configured
    URI -- so a caller could never point the command at another client, and the
    doc below would go to a real CouchDB instead of the transport stub.
    """

    def test_writes_the_worker_doc_through_the_configured_client(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(201, json={'ok': True})

        command = InstallWorkerCommand()
        command.set_settings({
            'couchdb_uri': 'http://cdb:5984', 'couchdb_db': 'desk_drawer',
            'worker_dns': 'sqlite:ns1.localhost',
        }, hostname='ns1.localhost')
        command.db.close()
        command.db = CouchDBClient.db(
            'http://cdb:5984', db_name='desk_drawer',
            transport=httpx.MockTransport(handler),
        )
        self.addCleanup(command.db.close)

        command.run()

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, '/desk_drawer/worker-ns1.localhost')
        self.assertEqual(json.loads(requests[0].content), {
            '_id': 'worker-ns1.localhost', 'type': 'worker',
            'hostname': 'ns1.localhost',
            'provides': {'domain': [{'backend': 'sqlite', 'name': 'ns1.localhost'}]},
        })


class DesignDocJavascriptTest(unittest.TestCase):
    """CouchDB 3.x rejects the SpiderMonkey-only JS that 1.6 used to accept.

    `for each (x in list)` was the one non-standard construct in these views;
    it made the whole design doc fail to install with a compilation_error.
    """

    def design_js(self):
        design = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '_design',
        )
        for root, _, files in os.walk(design):
            for name in sorted(files):
                if not name.endswith('.js'):
                    continue
                path = os.path.join(root, name)
                with open(path) as f:
                    yield os.path.relpath(path, design), f.read()

    def test_no_commented_out_emit(self):
        """FileDesignDocsLoader drops every line containing '//'.

        A commented-out emit therefore never reaches the installed design doc,
        so the view silently indexes less than its source suggests -- which is
        invisible until something that reads the view comes up empty.
        """
        offenders = []
        for path, source in self.design_js():
            for line in source.splitlines():
                comment = line.partition('//')[2]
                if 'emit(' in comment:
                    offenders.append(path)

        self.assertEqual(offenders, [])

    def test_the_version_view_indexes_documents_without_a_version(self):
        """`dworker migrate` walks the `version` view to find work.

        Legacy documents have no `version` property at all, so a map that only
        emits when the property exists makes migrate a no-op on exactly the
        documents that need it. Asserted against the design doc the loader
        builds, not the file: the loader is where the stripping happens.
        """
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        design_doc = FileDesignDocsLoader('_design/desk_drawer/').design_doc

        installed = design_doc['views']['version']['map']

        self.assertIn('else', installed)
        # the `if` branch and the `else` branch, both surviving the loader
        self.assertEqual(installed.count('emit('), 2)

    def test_no_spidermonkey_only_for_each(self):
        offenders = [
            path for path, source in self.design_js() if 'for each' in source
        ]

        self.assertEqual(offenders, [])


if __name__ == '__main__':
    unittest.main()
