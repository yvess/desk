# coding: utf-8
# python3
from __future__ import absolute_import, print_function
from __future__ import unicode_literals, division
from importlib import import_module
from datetime import date
from couchdbkit import Server
from desk.command import SettingsCommand
from desk.plugin.extcrm import Dummy
from desk.plugin.invoice.invoice import Invoice, InvoiceCycle


class CreateInvoicesCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        invoices_create_parser = subparsers.add_parser(
            'invoices-create',
            help="""Create invoices for recurring billing.""",
        )
        invoices_create_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )
        invoices_create_parser.add_argument(
            "-n", "--invoice_nr", dest="invoice_nr",
            default=1, type=int,
            help="start number for invoices"
        )
        invoices_create_parser.add_argument(
            "-d", "--invoice_main_domain", dest="invoice_one_domain",
            default=None,
            help="creates only invoice with main domain"
        )
        invoices_create_parser.add_argument(
            "-y", "--year", dest="year",
            default=date.today().year, type=int,
            help="year to bill"
        )

        invoices_create_parser.add_argument(
            "-m", "--max", dest="max",
            default=0, type=int,
            help="maximal number of invoices to create"
        )

        return invoices_create_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        crm = Dummy
        if 'worker_extcrm' in self.settings:
            crm_classname = self.settings.worker_extcrm.split(':')[0].title()
            Crm = import_module(".%s" % crm_classname, package="desk.plugin.extcrm")
            crm = Crm(self.settings)
        server = Server(self.settings.couchdb_uri)
        db = server.get_db(self.settings.couchdb_db)

        invoice_cycle = InvoiceCycle(self.settings.invoice_nr)
        clients = db.view(
            self._cmd("client_is_billable"), include_docs=True
        )
        counter = 0
        for result in clients:
            invoice = Invoice(
                self.settings, crm=crm,
                client_doc=result['doc'],
                invoice_cycle=invoice_cycle
            )
            if invoice.doc['services']['web']['start_date'] < \
               invoice_cycle.doc['end_date']:
               if invoice.doc['main_domain'] == self.settings.invoice_one_domain \
                or not self.settings.invoice_one_domain:
                invoice.render_pdf()
                invoice_cycle.add_invoice(invoice)
                counter += 1
                print(".", end="")
            if self.settings.max != 0 and counter >= self.settings.max:
                break
        print("\n", "total", invoice_cycle.get_total())
