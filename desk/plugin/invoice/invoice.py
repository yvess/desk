# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import codecs
import os
from collections import OrderedDict
from datetime import date, datetime
from unicodedata import normalize
from couchdbkit import Server
from weasyprint import HTML
from desk.plugin.invoice import filters
from desk.plugin.base import MergedDoc
from desk.utils import parse_date, calc_esr_checksum
from jinja2 import Environment, FileSystemLoader


def get_default(attribute, part, defaults, special_attribute=None, date_force_day=None):
    if special_attribute in part:
        value = part[special_attribute]
    elif attribute not in part:
        value = defaults[attribute]
    else:
        value = part[attribute]
    if attribute == 'price':
        value = float(value)
    if '_date' in attribute and not hasattr(value, 'year'):
        value = parse_date(value, force_day=date_force_day)
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
        self.extcrm_id = client_doc['extcrm_id']
        self.client_doc = client_doc
        self.settings = settings
        self.invoice_cycle = invoice_cycle
        self.invoice_nr = invoice_cycle.current_nr
        server = Server(self.settings.couchdb_uri)
        self.db = server.get_db(self.settings.couchdb_db)
        if not Invoice.service_definitons:
            Invoice.load_service_definitions(self.db)
        self.setup_invoice()

    def client_name_normalized(self):
        fname = normalize('NFKD', self.client_doc['name']).encode('ASCII', 'ignore').lower()
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
        if 'last_invoice_end_date' in self.client_doc:
            self.doc['last_invoice_end_date'] = parse_date(
                self.client_doc['last_invoice_end_date'], force_day='end')
        self.doc['services'] = self.get_services()
        self.doc['services_list'] = sorted([k for k in self.doc['services'].iterkeys()])
        self.doc['address'] = self.crm.get_address(self.extcrm_id)
        self.doc['client_name'] = self.client_doc['name']
        # import ipdb; ipdb.set_trace()

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
        cycle_start_date = self.invoice_cycle.doc['start_date']
        for result in self.db.view(
                self._cmd("service_by_client"),
                key=self.client_id, include_docs=True):
            service_doc = MergedDoc(self.db, result['doc']).doc
            service_def = Invoice.service_definitons[service_doc['service_type']]
            package = service_def['packages'][service_doc['package_type']]
            service_doc['price'] = get_default('price', service_doc, package)
            service_doc['package_title'] = get_default(
                'title', service_doc, package, special_attribute='package_title'
            )
            service_doc['title'] = get_default('title', service_doc, service_def)
            if 'start_date' in service_doc:
                service_start_date = parse_date(service_doc['start_date'], force_day='start')
            else:
                service_start_date = cycle_start_date
            if 'last_invoice_end_date' in self.doc:
                if service_start_date < self.doc['last_invoice_end_date']:
                    service_start_date = cycle_start_date
            service_doc['start_date'] = service_start_date
            service_doc['addons'] = self.add_addons(service_doc, service_def['addons'])
            service_doc['included'] = self.add_included(service_doc, package)
            service_end_date = get_default(
                'end_date', service_doc, self.doc)
            doc_amount = self.add_amount(
                service_doc['price'], service_doc['start_date'], service_end_date)
            service_doc.update(doc_amount)
            if service_doc['total'] == 0.0 \
               and not service_doc['addons'] \
               and not service_doc['included']:
                pass
            else:
                services[service_doc['service_type']] = service_doc
        if hasattr(self.settings, 'invoice_service_order'):
            servicesOrdered = OrderedDict()
            service_order = [s.strip() for s in self.settings.invoice_service_order.split(',')]
            for name in service_order:
                if name in services:
                    servicesOrdered[name] = services[name]
                    del services[name]
            if services:
                for k, v in services.iteritems():
                    servicesOrdered[k] = v
            return servicesOrdered
        return services

    def add_addons(self, service, sd_addons):
        addons = []
        cycle_start_date = self.invoice_cycle.doc['start_date']
        if 'addon_service_items' in service:
            for addon in service['addon_service_items']:
                if isinstance(addon, basestring):
                    addon = {'name': addon}
                elif isinstance(addon, dict):
                    pass
                else:
                    raise
                addon['price'] = get_default('price', addon, sd_addons[addon['itemType']])
                addon['title'] = get_default('title', addon, sd_addons[addon['itemType']])
                addon['start_date'] = get_default(
                    'start_date', addon, service,
                    special_attribute='startDate', date_force_day='start'
                )
                if 'last_invoice_end_date' in self.doc:
                    if addon['start_date'] < self.doc['last_invoice_end_date']:
                        addon['start_date'] = cycle_start_date
                else:
                    if addon['start_date'] < self.doc['start_date']:
                        addon['start_date'] = self.doc['start_date']
                addon['end_date'] = get_default(
                    'end_date', addon, self.doc,
                    special_attribute='endDate',
                )
                addon.update(
                    self.add_amount(addon['price'], addon['start_date'], addon['end_date'])
                )
                if not addon['start_date'] > self.invoice_cycle.doc['end_date']:
                    addons.append(addon)
            del(service['addon_service_items'])
        return addons

    def add_included(self, service, sd_package):
        included = []
        if 'included_service_items' in service:
            for item in service['included_service_items']:
                item['title'] = get_default(
                    'title', item, sd_package["included"][item['itemType']]
                )
                included.append(item)
            del(service['included_service_items'])
        return included

    def add_amount(self, price, start_date, end_date):
        item = {}
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
