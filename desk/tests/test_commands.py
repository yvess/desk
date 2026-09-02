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
from unittest.mock import patch

import httpx

from desk.command import MigrateCommand
from desk.plugin.base import MergedDoc
from desk.plugin.dns.cmd_powerdns import PowerdnsRebuildCommand
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
            invoice_nr=100, invoice_date='2026-12-31', invoice_tax='0.0',
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
        self.assertEqual(migrated['state'], 'new')
        self.assertNotIn('active_rev', migrated)

    def test_it_stops_when_no_further_migration_exists(self):
        # to0002 does not exist, so version 1 is the end of the chain
        self.assertEqual(len(self.couch.written()), 1)


class StubPowerdns:
    """Records what dns-rebuild-powerdns asks the backend to do."""

    map_doc_id = 'map-ips'

    def __init__(self):
        self.doc = None
        self.calls = []
        self.lookup_map = None

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append(name)
        return record

    def set_lookup_map(self, doc):
        self.lookup_map = doc['map']

    def get_soa_serial(self):
        self.calls.append('get_soa_serial')
        return '2026090100'


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
                    'a': [{'host': 'www', 'ip': '$ip_web'}],
                },
            },
        )
        self.command = PowerdnsRebuildCommand()
        self.command.set_settings(settings(db='/tmp/pdns.sqlite3', target=None))
        self.command.db.close()
        self.command.db = self.couch.client()
        self.addCleanup(self.command.db.close)
        self.command.pdns = StubPowerdns()

    def test_rebuild_merges_the_domain_with_its_template(self):
        self.command._rebuild('test.ch')
        self.assertEqual(self.command.pdns.doc['domain'], 'test.ch')
        self.assertEqual(self.command.pdns.doc['nameservers'], ['ns1.test.ch'])

    def test_rebuild_deletes_before_it_recreates(self):
        self.command._rebuild('test.ch')
        self.assertEqual(
            self.command.pdns.calls,
            ['set_domain', 'get_soa_serial', 'del_domain', 'create',
             'update_soa'],
        )

    def test_rebuild_without_pre_delete_only_creates(self):
        self.command._rebuild('test.ch', pre_delete=False)
        self.assertEqual(self.command.pdns.calls, ['create', 'update_soa'])

    def run_command(self):
        with patch(
            'desk.plugin.dns.cmd_powerdns.Powerdns',
            return_value=self.command.pdns,
        ):
            with redirect_stdout(io.StringIO()):
                with patch('builtins.input', return_value='no'):
                    self.command.run()

    def test_the_lookup_map_is_read_as_a_document(self):
        self.run_command()
        self.assertEqual(self.command.pdns.lookup_map, {'$ip_web': '1.2.3.4'})

    def test_a_missing_lookup_map_aborts_the_run(self):
        """httpx does not raise on the 404; the run used to fail later
        with KeyError: 'map'."""
        del self.couch.docs['map-ips']
        with self.assertRaises(httpx.HTTPStatusError) as raised:
            self.run_command()
        self.assertIn('map-ips', str(raised.exception))
        self.assertIsNone(self.command.pdns.lookup_map)

    def test_rebuild_of_an_unknown_domain_names_it(self):
        """An empty view result used to raise a bare IndexError."""
        self.couch.views['domain_by_name'] = []
        with self.assertRaises(LookupError) as raised:
            self.command._rebuild('nosuch.ch')
        self.assertIn('nosuch.ch', str(raised.exception))
        self.assertEqual(self.command.pdns.calls, [])


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


if __name__ == '__main__':
    unittest.main()
