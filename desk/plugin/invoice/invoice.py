# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import codecs
from datetime import date
from couchdbkit import Server
from weasyprint import HTML
from desk.plugin.invoice import filters
from desk.plugin.base import MergedDoc
from desk.utils import parse_date, calc_esr_checksum
from jinja2 import Environment, FileSystemLoader


class Invoice(object):
    """Invoice for generating HTML and PDF"""
    def __init__(self, settings, crm, client_doc, invoice_cycle):
        self.invoice_template_dir = settings.invoice_template_dir
        self.output_dir = settings.invoice_output_dir
        self.tax = float(settings.invoice_tax)
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.invoice_template_dir)
        )
        self.jinja_env.filters['nl2br'] = filters.nl2br
        self.jinja_env.filters['format_date'] = filters.format_date
        self.crm = crm
        self.client_id = client_doc['_id']
        self.extcrm_id = client_doc['extcrm_id']
        self.settings = settings
        self.invoice_cycle = invoice_cycle
        self.invoice_nr = invoice_cycle.current_nr
        server = Server(self.settings.couchdb_uri)
        self.db = server.get_db(self.settings.couchdb_db)
        self.setup_invoice()

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def setup_invoice(self):
        self.doc = {
            'start_date': self.invoice_cycle.doc['start_date'],
            'end_date': self.invoice_cycle.doc['end_date'],
            'date': date.today(),
            'nr': self.invoice_nr,
            'ref_nr': "%s%s" % (
                self.invoice_nr,
                calc_esr_checksum(self.invoice_nr)
            ),
            'amount': 0.0,
            'tax': 0.0,
            'total': 0.0
        }
        self.doc['services'] = self.get_services()
        self.doc['address'] = self.crm.get_address(self.extcrm_id)
        main_domain = self.doc['services']['web']['items'][0]
        if isinstance(main_domain, dict) and 'name' in main_domain:
            main_domain = main_domain['name']
        self.doc['main_domain'] = main_domain
        if 'last_invoice_end_date' in self.doc:
            self.doc['last_invoice_end_date'] = (
                parse_date(self.doc['last_invoice_end_date'])
            )

    def render_pdf(self):
        tpl = self.jinja_env.get_template('invoice_tpl.html')
        self.invoice_fname = "{date}_CHF{total:.2f}_Nr{nr}_hosting-{domain}_ta".format(
            date=self.doc['date'].strftime("%Y-%m-%d"),
            total=self.doc['total'],
            nr=self.doc['nr'],
            domain=self.doc['main_domain']
        )
        with codecs.open(
            '%s/html/%s.html' % (self.output_dir, self.invoice_fname),
            'w+', encoding="utf-8"
        ) as invoice_html:
            invoice_html.write(tpl.render(**self.doc))
            invoice_html.seek(0)
            base_url = "%s/html" % self.invoice_template_dir
            html = HTML(invoice_html, base_url=base_url)
            html.write_pdf('%s/pdf/%s.pdf' % (self.output_dir, self.invoice_fname))

    def get_services(self):
        services = {}
        for result in self.db.view(
                self._cmd("service_by_client"),
                key=self.client_id, include_docs=True):
            service_doc = MergedDoc(self.db, result['doc']).doc
            invoice_start_date = parse_date(service_doc['start_date'])
            if invoice_start_date < self.invoice_cycle.doc['start_date']:
                invoice_start_date = self.invoice_cycle.doc['start_date']
            service_doc['start_date'] = invoice_start_date
            self.add_package(service_doc)
            service_doc['addons'] = self.add_addons(service_doc)
            service_doc.update(self.add_amount(
                service_doc['price'], service_doc['start_date'])
            )
            services[service_doc['service_type']] = service_doc
        return services

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
                if hasattr(self.settings, title_attr) and not 'title' in addon:
                    title = getattr(self.settings, title_attr)
                    addon['title'] = title
                if 'start_date' not in addon:
                    addon['start_date'] = service['start_date']
                else:
                    addon['start_date'] = parse_date(addon['start_date'])
                addon.update(
                    self.add_amount(
                        addon['price'], addon['start_date']
                    )
                )
                if not addon['start_date'] > self.invoice_cycle.doc['end_date']:
                    addons.append(addon)
            return addons

    def add_amount(self, price, start_date):
        end_date = self.doc['end_date']
        item = {}
        if ('last_invoice_end_date' in self.doc
           and start_date < self.doc['start_date']):
            start_date = self.doc['start_date']
        months = (
            (end_date.year - start_date.year) * 12 +
            (end_date.month - start_date.month) + 1
        )
        if months < 0:
            months = 0
        item['months'] = months
        item['amount'] = months * price
        item['tax'] = item['amount'] * self.tax
        item['total'] = item['amount'] + item['tax']
        self.doc['amount'] += item['amount']
        self.doc['tax'] += item['tax']
        self.doc['total'] += item['total']
        return item


class InvoiceCycle(object):
    """One Invoice Run for a given period"""
    def __init__(self, invoice_nr):
        self.start_nr = invoice_nr
        self.current_nr = self.start_nr
        self.invoices = []
        self.doc = {
            'start_date': date(2014, 1, 1), # TODO not hardcode
            'end_date': date(2014, 12, 31), # TODO not hardcode
        }

    def add_invoice(self, invoice):
        self.invoices.append(invoice)
        self.current_nr += 1

    def get_total(self):
        return sum([i.doc['total'] for i in self.invoices])
