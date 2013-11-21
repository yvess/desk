# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division

from datetime import date
import codecs
from couchdbkit import Server
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from desk.utils import parse_date
from desk.cmd import SettingsCommand
from desk.plugin.extcrm.todoyu import Todoyu
from desk.plugin.invoice import filters
from desk.plugin.base import MergedDoc


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

    def _get_services(self, client_id):
        services = {}
        for result in self.db.view(
                self._cmd("service_by_client"),
                key=client_id, include_docs=True):
            doc = MergedDoc(self.db, result['doc']).doc
            doc = self.add_invoice_data(doc)
            services[doc['service_type']] = doc
        return services

    def calc_esr_checksum(self, ref_number):
        ref_number = str(int(ref_number))  # removed leading zeros
        quasigroup_esr = (0, 9, 4, 6, 8, 2, 7, 1, 3, 5)
        sum = 0

        for n in ref_number:
            sum = quasigroup_esr[(sum + int(n)) % 10]
        return (10 - sum) % 10

    def add_package(self, service):
        if 'package' in service:
            price_attr = "service_{}_package_{}_price".format(
                service['service_type'], service['package']
            )
            service['price'] = float(getattr(self.settings, price_attr))
            title_attr = "service_{}_package_{}_title".format(
                service['service_type'], service['package']
            )
            if hasattr(self.settings, title_attr):
                service['title'] = getattr(self.settings, title_attr)

    def add_addons(self, service):
        if 'addons' in service:
            addons = []
            for addon in service['addons']:
                if isinstance(addon, basestring):
                    addon = {'name': addon}
                elif isinstance(addon, dict):
                    pass
                else:
                    raise
                if 'price' not in addon:
                    price_attr = "service_{}_addon_{}_price".format(
                        service['service_type'], addon['name']
                    )
                    addon['price'] = float(getattr(self.settings, price_attr))
                title_attr = "service_{}_addon_{}_title".format(
                    service['service_type'], addon['name']
                )
                if hasattr(self.settings, title_attr):
                    title = getattr(self.settings, title_attr)
                    addon['title'] = title
                if 'start_date' not in addon:
                    addon['start_date'] = self.invoice['start_date']
                else:
                    addon['start_date'] = parse_date(addon['start_date'])
                addon.update(
                    self.add_amount(
                        addon['price'], addon['start_date']
                    )
                )
                addons.append(addon)
            return addons

    def add_invoice_data(self, service):
        self.add_package(service)
        service['addons'] = self.add_addons(service)
        service['start_date'] = parse_date(service['start_date'])
        service.update(self.add_amount(
            service['price'], service['start_date'])
        )

        return service

    def add_amount(self, price, start_date):
        end_date = self.invoice['end_date']
        item = {}
        if start_date > self.invoice['start_date']:
            start_date = start_date
        months = (
            (end_date.year - start_date.year) * 12 +
            (end_date.month - start_date.month) + 1
        )
        item['months'] = months
        item['amount'] = months * price
        item['tax'] = item['amount'] * self.tax
        item['total'] = item['amount'] + item['tax']
        self.invoice['amount'] += item['amount']
        self.invoice['tax'] += item['tax']
        self.invoice['total'] += item['total']
        return item

    def run(self):
        todoyu = Todoyu(self.settings)
        server = Server(self.settings.couchdb_uri)
        self.db = server.get_db(self.settings.couchdb_db)
        invoice_template_dir = self.settings.invoice_template_dir
        output_dir = self.settings.invoice_output_dir
        self.tax = float(self.settings.invoice_tax)
        jinja_env = Environment(loader=FileSystemLoader(invoice_template_dir))
        jinja_env.filters['nl2br'] = filters.nl2br
        jinja_env.filters['format_date'] = filters.format_date

        self.invoice_nr = self.settings.invoice_nr
        query_results = self.db.view(
            self._cmd("client_is_billable"), include_docs=True
        )
        all_total = 0.0
        docs = []
        # if self.settings.max != 0:
        #     query_results = query_results[:self.settings.max]
        counter = 0
        for result in query_results:
            self.invoice = {
                'start_date': date(self.settings.year, 1, 1),
                'end_date': date(self.settings.year, 12, 31),
                'date': date.today(),
                'nr': self.invoice_nr,
                'ref_nr': "%s%s" % (
                    self.invoice_nr,
                    self.calc_esr_checksum(self.invoice_nr)
                ),
                'amount': 0.0,
                'tax': 0.0,
                'total': 0.0
            }
            self.invoice['services'] = self._get_services(result['doc']['_id'])
            self.invoice['address'] = todoyu.get_address(result['doc']['extcrm_id'])

            t = jinja_env.get_template('invoice_tpl.html')
            main_domain = self.invoice['services']['web']['items'][0]
            if isinstance(main_domain, dict) and 'name' in main_domain:
                main_domain = main_domain['name']
            self.invoice['main_domain'] = main_domain
            invoice_name = "{date}_CHF{total:.2f}_Nr{nr}_hosting-{domain}_ta".format(
                date=self.invoice['date'].strftime("%Y-%m-%d"),
                total=self.invoice['total'],
                nr=self.invoice['nr'],
                domain=main_domain
            )
            with codecs.open(
                '%s/html/%s.html' % (output_dir, invoice_name),
                'w+', encoding="utf-8"
            ) as invoice_html:
                invoice_html.write(t.render(**self.invoice))
                invoice_html.seek(0)
                html = HTML(invoice_html, base_url="%s/html" % invoice_template_dir)
                html.write_pdf('%s/pdf/%s.pdf' % (output_dir, invoice_name))
                self.invoice_nr += 1
                counter += 1

            all_total += self.invoice['total']
            print(".", end="")
            if self.settings.max != 0 and counter >= self.settings.max:
                break
        print("\n", "total", all_total)
