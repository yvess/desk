# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import codecs
import os
from datetime import date, datetime
from unicodedata import normalize
from couchdbkit import Server
from weasyprint import HTML
from desk.plugin.invoice import filters
from desk.plugin.base import MergedDoc
from desk.utils import parse_date, calc_esr_checksum
from jinja2 import Environment, FileSystemLoader


def get_default(attribute, part, defaults):
    if attribute not in part:
        value = defaults[attribute]
    else:
        value = part[attribute]
    if attribute == 'price':
        value = float(value)
    if '_date' in attribute and not hasattr(value, 'year'):
        value = parse_date(value)
    return value


class Invoice(object):
    service_definitons = {}

    @classmethod
    def load_service_definitions(cls, db):
        service_definitons_results = db.view(
            "%s/%s" % (db.dbname, "service_definition"),
            include_docs=True
        )
        for sd in service_definitons_results:
            cls.service_definitons[sd['doc']['service_type']] = sd['doc']

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
        self.client_name = client_doc['name']
        self.extcrm_id = client_doc['extcrm_id']
        self.settings = settings
        self.invoice_cycle = invoice_cycle
        self.invoice_nr = invoice_cycle.current_nr
        server = Server(self.settings.couchdb_uri)
        self.db = server.get_db(self.settings.couchdb_db)
        if not Invoice.service_definitons:
            Invoice.load_service_definitions(self.db)
        self.setup_invoice()

    def client_name_normalized(self):
        fname = normalize('NFKD', self.client_name).encode('ASCII', 'ignore').lower()
        fname = fname.replace(" ", "-")
        return fname

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
        self.doc['services_list'] = sorted([k for k in self.doc['services'].iterkeys()])
        self.doc['address'] = self.crm.get_address(self.extcrm_id)
        self.doc['client_name'] = self.client_name
        if 'last_invoice_end_date' in self.doc:
            self.doc['last_invoice_end_date'] = (
                parse_date(self.doc['last_invoice_end_date'])
            )

    def render_pdf(self):
        tpl = self.jinja_env.get_template('invoice_tpl.html')
        self.invoice_fname = "{date}_CHF{total:.2f}_Nr{nr}_hosting-{name}_ta".format(
            date=self.doc['date'].strftime("%Y-%m-%d"),
            total=self.doc['total'],
            nr=self.doc['nr'],
            name=self.client_name_normalized()
        )
        for file_format in ['html', 'pdf']:
            path = "%s/%s" % (self.output_dir, file_format)
            if not os.path.exists(path):
                os.mkdir(path)
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
            service_def = Invoice.service_definitons[service_doc['service_type']]
            package = service_def['packages'][service_doc['package_type']]
            service_doc['price'] = get_default('price', service_doc, package)
            service_doc['package_title'] = get_default('title', service_doc, package)
            service_doc['title'] = get_default('title', service_doc, service_def)
            invoice_start_date = parse_date(service_doc['start_date'])
            if invoice_start_date < self.invoice_cycle.doc['start_date']:
                invoice_start_date = self.invoice_cycle.doc['start_date']
            service_doc['start_date'] = invoice_start_date
            service_doc['addons'] = self.add_addons(service_doc, service_def['addons'])
            service_doc.update(self.add_amount(
                service_doc['price'], service_doc['start_date'])
            )
            services[service_doc['service_type']] = service_doc
        return services

    def add_addons(self, service, sd_addons):
        if 'addon_service_items' in service:
            addons = []
            for addon in service['addon_service_items']:
                if isinstance(addon, basestring):
                    addon = {'name': addon}
                elif isinstance(addon, dict):
                    pass
                else:
                    raise
                addon['price'] = get_default('price', addon, sd_addons[addon['itemType']])
                addon['title'] = get_default('title', addon, sd_addons[addon['itemType']])
                addon['start_date'] = get_default('start_date', addon, service)
                addon.update(
                    self.add_amount(
                        addon['price'], addon['start_date']
                    )
                )
                if not addon['start_date'] > self.invoice_cycle.doc['end_date']:
                    addons.append(addon)
            del(service['addon_service_items'])
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
        current_year = datetime.now().year  # TODO create setting
        self.doc = {
            'start_date': date(current_year, 1, 1),
            'end_date': date(current_year, 12, 31),
        }

    def add_invoice(self, invoice):
        self.invoices.append(invoice)
        self.current_nr += 1

    def get_total(self):
        return sum([i.doc['total'] for i in self.invoices])
