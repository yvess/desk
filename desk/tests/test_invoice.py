"""Regression tests for the invoice logic merged from master (M1).

Covers the four behaviours that arrived with the merge:
  fb49e67 addon / included item start+end dates  -> set_item_period()
  7541c38 price-change safeguard                 -> package_price / price_overwritten
  d39ba8f drop empty services and addons
  d01a881 invoice_ref on the invoice doc

Fixtures are plain dicts shaped like the CouchDB docs the `service_by_client`
view returns, served over httpx.MockTransport, so no database is needed.
"""
import io
import unittest
from contextlib import redirect_stdout
from datetime import date

import httpx

from desk.plugin.extcrm.dummy import Dummy
from desk.plugin.invoice.invoice import Invoice, InvoiceCycle
from desk.utils import CouchDBClient, ObjectDict

YEAR = 2026

SERVICE_DEFINITIONS = {
    'hosting': {
        'service_type': 'hosting',
        'title': 'Hosting',
        'packages': {
            'basic': {
                'title': 'Basic',
                'price': '10.00',
                'included': {'domain': {'title': 'Domain inklusive'}},
            },
        },
        'addons': {'mailbox': {'title': 'Mailbox', 'price': '2.00'}},
    },
}


def make_service(**overrides):
    doc = {
        '_id': 'service-1',
        'type': 'service',
        'client_id': 'client-1',
        'service_type': 'hosting',
        'package_type': 'basic',
    }
    doc.update(overrides)
    return doc


def couch_client(service_docs):
    """A CouchDBClient whose CouchDB answers every view with these services."""

    def handler(request):
        return httpx.Response(
            200, json={'rows': [{'doc': doc} for doc in service_docs]}
        )

    return CouchDBClient.db(
        'http://cdb:5984', db_name='desk_drawer',
        transport=httpx.MockTransport(handler),
    )


class InvoiceTestCaseBase(unittest.TestCase):
    def setUp(self):
        self._saved_defs = Invoice.service_definitons
        Invoice.service_definitons = SERVICE_DEFINITIONS

    def tearDown(self):
        Invoice.service_definitons = self._saved_defs

    def make_invoice(self, service_docs=(), client_doc=None, tax=0.0):
        # __init__ renders the whole invoice; the object is assembled directly
        # here so each test can call setup_invoice() and look at the result.
        invoice = object.__new__(Invoice)
        cycle = InvoiceCycle(1, YEAR)
        invoice.tax = tax
        invoice.crm = Dummy()
        invoice.settings = ObjectDict(
            couchdb_db='desk_drawer', invoice_date=f'{YEAR}-12-31'
        )
        invoice.client_doc = client_doc or {'_id': 'client-1', 'name': 'test client'}
        invoice.client_id = invoice.client_doc['_id']
        invoice.extcrm_id = 'p1'
        invoice.invoice_cycle = cycle
        invoice.invoice_nr = 1
        invoice.db = couch_client(list(service_docs))
        self.addCleanup(invoice.db.close)
        return invoice

    def services_of(self, invoice):
        return invoice.doc['services'].get('hosting', {}).get('items', [])


class PriceSafeguardTestCase(InvoiceTestCaseBase):
    """7541c38 — the package list price is kept next to the effective price."""

    def test_price_falls_back_to_the_package(self):
        invoice = self.make_invoice([make_service()])
        invoice.setup_invoice()
        service = self.services_of(invoice)[0]
        self.assertEqual(service['price'], 10.0)
        self.assertEqual(service['package_price'], 10.0)
        self.assertFalse(service['price_overwritten'])

    def test_own_price_is_flagged_as_overwritten(self):
        invoice = self.make_invoice([make_service(price='15.00')])
        invoice.setup_invoice()
        service = self.services_of(invoice)[0]
        self.assertEqual(service['price'], 15.0)
        self.assertEqual(service['package_price'], 10.0)
        self.assertTrue(service['price_overwritten'])

    def test_own_price_equal_to_the_package_is_not_overwritten(self):
        invoice = self.make_invoice([make_service(price='10.00')])
        invoice.setup_invoice()
        self.assertFalse(self.services_of(invoice)[0]['price_overwritten'])

    def test_empty_price_falls_back_instead_of_raising(self):
        """An empty price string used to reach float('') and raise ValueError."""
        invoice = self.make_invoice([make_service(price='')])
        invoice.setup_invoice()
        service = self.services_of(invoice)[0]
        self.assertEqual(service['price'], 10.0)
        self.assertFalse(service['price_overwritten'])


class ItemPeriodTestCase(InvoiceTestCaseBase):
    """fb49e67 — an item is billed inside the period of its service."""

    def setUp(self):
        super().setUp()
        self.invoice = self.make_invoice()
        self.service = {
            'start_date': date(YEAR, 3, 1),
            'end_date': date(YEAR, 9, 30),
        }

    def test_item_without_dates_takes_the_service_period(self):
        item = {'itemType': 'mailbox'}
        self.assertTrue(self.invoice.set_item_period(item, self.service))
        self.assertEqual(item['start_date'], date(YEAR, 3, 1))
        self.assertEqual(item['end_date'], date(YEAR, 9, 30))

    def test_item_cannot_start_before_its_service(self):
        item = {'itemType': 'mailbox', 'startDate': f'{YEAR}-01-15'}
        self.assertTrue(self.invoice.set_item_period(item, self.service))
        self.assertEqual(item['start_date'], date(YEAR, 3, 1))

    def test_later_item_start_wins(self):
        item = {'itemType': 'mailbox', 'startDate': f'{YEAR}-05-17'}
        self.assertTrue(self.invoice.set_item_period(item, self.service))
        # startDate is forced to the first of the month
        self.assertEqual(item['start_date'], date(YEAR, 5, 1))

    def test_item_cannot_end_after_its_service(self):
        item = {'itemType': 'mailbox', 'endDate': f'{YEAR}-12-31'}
        self.assertTrue(self.invoice.set_item_period(item, self.service))
        self.assertEqual(item['end_date'], date(YEAR, 9, 30))

    def test_earlier_item_end_wins(self):
        item = {'itemType': 'mailbox', 'endDate': f'{YEAR}-06-30'}
        self.assertTrue(self.invoice.set_item_period(item, self.service))
        self.assertEqual(item['end_date'], date(YEAR, 6, 30))

    def test_item_outside_the_service_period_is_inactive(self):
        item = {'itemType': 'mailbox', 'startDate': f'{YEAR}-11-01'}
        self.assertFalse(self.invoice.set_item_period(item, self.service))


class DropEmptyTestCase(InvoiceTestCaseBase):
    """d39ba8f — services and addons that bill nothing are left out."""

    def test_addon_billing_zero_is_dropped(self):
        service = make_service(addon_service_items=[
            {'itemType': 'mailbox', 'price': '0.00'},
            {'itemType': 'mailbox', 'price': '2.00'},
        ])
        invoice = self.make_invoice([service])
        invoice.setup_invoice()
        addons = self.services_of(invoice)[0]['addons']
        self.assertEqual([a['price'] for a in addons], [2.0])

    def test_addon_outside_the_service_period_is_dropped(self):
        service = make_service(
            end_date=f'{YEAR}-06-30',
            addon_service_items=[
                {'itemType': 'mailbox', 'price': '2.00', 'startDate': f'{YEAR}-09-01'},
            ],
        )
        invoice = self.make_invoice([service])
        invoice.setup_invoice()
        self.assertEqual(self.services_of(invoice)[0]['addons'], [])

    def test_service_billing_zero_is_dropped(self):
        invoice = self.make_invoice([make_service(price='0.00')])
        invoice.setup_invoice()
        self.assertEqual(invoice.doc['services'], {})
        self.assertEqual(invoice.doc['services_list'], [])

    def test_service_billing_zero_is_kept_when_it_has_included_items(self):
        """A bundled service still has to show up with what it includes."""
        service = make_service(
            price='0.00',
            included_service_items=[{'itemType': 'domain'}],
        )
        invoice = self.make_invoice([service])
        invoice.setup_invoice()
        billed = self.services_of(invoice)
        self.assertEqual(len(billed), 1)
        self.assertEqual(billed[0]['included'][0]['title'], 'Domain inklusive')

    def test_service_billing_zero_is_kept_when_an_addon_bills(self):
        service = make_service(
            price='0.00',
            addon_service_items=[{'itemType': 'mailbox', 'price': '2.00'}],
        )
        invoice = self.make_invoice([service])
        invoice.setup_invoice()
        self.assertEqual(len(self.services_of(invoice)), 1)

    def test_a_malformed_addon_names_the_service(self):
        """A bare `raise` used to give 'No active exception to reraise'."""
        invoice = self.make_invoice([make_service(addon_service_items=[None])])
        with self.assertRaises(TypeError) as raised:
            invoice.setup_invoice()
        self.assertIn('service-1', str(raised.exception))

    def test_raw_item_lists_are_removed_from_the_service_doc(self):
        service = make_service(
            addon_service_items=[{'itemType': 'mailbox', 'price': '2.00'}],
            included_service_items=[{'itemType': 'domain'}],
        )
        invoice = self.make_invoice([service])
        invoice.setup_invoice()
        billed = self.services_of(invoice)[0]
        self.assertNotIn('addon_service_items', billed)
        self.assertNotIn('included_service_items', billed)
        self.assertEqual(billed['included'][0]['months'], 12)


class FilenameTestCase(InvoiceTestCaseBase):
    """The client name in the pdf filename is ascii, lower case, no spaces."""

    def test_client_name_normalized_is_a_str(self):
        # under python 3 .encode() gave bytes and .replace(' ', '-') raised
        invoice = self.make_invoice(
            client_doc={'_id': 'client-1', 'name': 'Müller & Söhne AG'}
        )
        self.assertEqual(invoice.client_name_normalized(), 'muller-&-sohne-ag')


class MissingExtcrmIdTestCase(InvoiceTestCaseBase):
    """A client without extcrm_id has to stay skippable, not crash the run."""

    def test_invoice_without_extcrm_id_is_marked_unusable(self):
        settings = ObjectDict(
            invoice_template_dir='.', invoice_output_dir='.', invoice_tax='0.0'
        )
        with redirect_stdout(io.StringIO()):
            invoice = Invoice(
                settings, crm=Dummy(),
                client_doc={'_id': 'client-1', 'name': 'no crm client'},
                invoice_cycle=InvoiceCycle(1, YEAR),
                db=None,  # the client is unusable before any view is read
            )
        # invoices-create keys its skip on client_doc: setup_invoice never ran,
        # so reading invoice.doc would raise AttributeError instead.
        self.assertIsNone(invoice.client_doc)
        self.assertFalse(hasattr(invoice, 'doc'))


class InvoiceRefTestCase(InvoiceTestCaseBase):
    """d01a881 — the client's invoice_ref is carried onto the invoice."""

    def test_invoice_ref_is_taken_from_the_client(self):
        invoice = self.make_invoice(
            [make_service()],
            client_doc={'_id': 'client-1', 'name': 'test client', 'invoice_ref': 'PO-42'},
        )
        invoice.setup_invoice()
        self.assertEqual(invoice.doc['invoice_ref'], 'PO-42')

    def test_invoice_ref_defaults_to_empty(self):
        invoice = self.make_invoice([make_service()])
        invoice.setup_invoice()
        self.assertEqual(invoice.doc['invoice_ref'], '')


class AmountTestCase(InvoiceTestCaseBase):
    """The merged date handling has to survive into the billed amount."""

    def test_full_year_is_twelve_months(self):
        invoice = self.make_invoice([make_service()])
        invoice.setup_invoice()
        service = self.services_of(invoice)[0]
        self.assertEqual(service['months'], 12)
        self.assertEqual(service['amount'], 120.0)
        self.assertEqual(invoice.doc['amount'], 120.0)

    def test_service_ending_mid_year_is_billed_pro_rata(self):
        invoice = self.make_invoice([make_service(end_date=f'{YEAR}-06-30')])
        invoice.setup_invoice()
        service = self.services_of(invoice)[0]
        self.assertEqual(service['months'], 6)
        self.assertEqual(service['amount'], 60.0)


if __name__ == '__main__':
    unittest.main()
