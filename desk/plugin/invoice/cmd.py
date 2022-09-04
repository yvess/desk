import os
from pathlib import Path
from datetime import date
from desk.command import SettingsCommand
from desk.utils import get_crm_module
from desk.plugin.invoice.invoice import Invoice, InvoiceCycle
from desk.plugin.invoice.qrbill import InvoiceQrBill


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
            "-id", "--invoice-date", dest="invoice_date",
            default=str(date.today()),
            help="overwrite invoice date (default: today)"
        )
        invoices_create_parser.add_argument(
            "-m", "--max", dest="max",
            default=0, type=int,
            help="maximal number of invoices to create"
        )

        invoices_create_parser.add_argument(
            "-l", "--limit", dest="limit_client_id",
            default=None,
            help="only create invoice for one client"
        )

        return invoices_create_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        crm = get_crm_module(self.settings)
        server = Server(self.settings.couchdb_uri)
        db = server.get_db(self.settings.couchdb_db)

        invoice_cycle = InvoiceCycle(self.settings.invoice_nr)
        clients = db.view(
            self._cmd("client_is_billable"), include_docs=True
        )
        counter = 0
        for client in clients:
            if not self.settings.limit_client_id or client['id'] == self.settings.limit_client_id:
                # print(client['doc']['name'])
                invoice = Invoice(
                    self.settings, crm=crm,
                    client_doc=client['doc'],
                    invoice_cycle=invoice_cycle
                )
                invoice_start_date = min(
                    [d['start_date'] for d in invoice.doc['services'].values()]
                )
                if invoice_start_date < invoice_cycle.doc['end_date']:
                    invoice.render_pdf()
                    invoice_cycle.add_invoice(invoice)
                    counter += 1
                    print(".", end="")
                if self.settings.max != 0 and counter >= self.settings.max:
                    break
        print("\n", "total", invoice_cycle.get_total())


class QrBillInvoicesCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        invoices_qrbill_parser = subparsers.add_parser(
            'invoices-qrbill',
            help="""add qrbill to pdfs""",
        )
        invoices_qrbill_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )
        invoices_qrbill_parser.add_argument(
            dest="invoices_pdf_path",
            default=None,
            help="invoices pdf path"
        )

        return invoices_qrbill_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        invoices_pdf_path = Path(self.settings.invoices_pdf_path)
        invoices = list(Path(invoices_pdf_path).glob('*.pdf'))
        for invoice in invoices:
            InvoiceQrBill(self.settings, invoices_pdf_path).add_qrbill(invoice)
