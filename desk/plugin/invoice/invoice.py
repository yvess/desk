import codecs
import os
from collections import OrderedDict
from datetime import date, datetime
from unicodedata import normalize
from weasyprint import HTML
from desk.plugin.invoice import filters
from desk.plugin.base import MergedDoc
from desk.utils import parse_date, calc_esr_checksum, AttributeDict
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
            "service_definition", include_docs=True
        )
        for sd in service_definitons_results:
            cls.service_definitons[sd['doc']['service_type']] = sd['doc']

    """Invoice for generating HTML and PDF"""
    def __init__(self, settings, crm, client_doc, invoice_cycle, db):
        self.invoice_template_dir = settings.invoice_template_dir
        self.output_dir = settings.invoice_output_dir
        self.tax = float(settings.invoice_tax)
        self.home_country = settings.invoice_home_country if hasattr(settings, 'invoice_home_country', ) else None
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.invoice_template_dir)
        )
        self.jinja_env.filters['nl2br'] = filters.nl2br
        self.jinja_env.filters['format_date'] = filters.format_date
        self.crm = crm
        self.client_id = client_doc['_id']
        try:
            self.extcrm_id = client_doc['extcrm_id']
        except KeyError:
            extcrm_id = client_doc['extcrm_id'] if 'extcrm_id' in client_doc else "None"
            print('\nNOT creating invoice missing extcrm_id:%s, %s' % (extcrm_id, client_doc['name']), client_doc)
            self.client_doc = None
            return
        self.client_doc = client_doc
        self.settings = settings
        self.invoice_cycle = invoice_cycle
        self.invoice_nr = invoice_cycle.current_nr
        self.db = db
        if not Invoice.service_definitons:
            Invoice.load_service_definitions(self.db)
        self.setup_invoice()

    def client_name_normalized(self):
        fname = normalize('NFKD', self.client_doc['name'])
        fname = fname.encode('ASCII', 'ignore').decode('ASCII').lower()
        return fname.replace(" ", "-")

    def setup_invoice(self):
        ref_nr = "%s%s" % (
            self.invoice_nr,
            calc_esr_checksum(self.invoice_nr)
        )
        ref_nr = ref_nr.rjust(25,"0")
        n = 5
        ref_nr = " ".join([ref_nr[i:i+n] for i in range(0, len(ref_nr), n)])
        ref_nr = "00 %s" % ref_nr
        self.doc = {
            'start_date': self.invoice_cycle.doc['start_date'],
            'end_date': self.invoice_cycle.doc['end_date'],
            'date': date(*[int(part) for part in self.settings.invoice_date.split('-')]),
            'nr': self.invoice_nr,
            'ref_nr': ref_nr,
            'amount': 0.0,
            'tax': 0.0,
            'total': 0.0
        }
        if 'last_invoice_end_date' in self.client_doc:
            self.doc['last_invoice_end_date'] = parse_date(
                self.client_doc['last_invoice_end_date'], force_day='end')
        self.doc['services'] = self.get_services()
        self.doc['services_list'] = sorted([k for k in self.doc['services'].keys()])
        try:
            self.doc['address'] = self.crm.get_address(self.extcrm_id)
        except KeyError:
            self.client_doc = None
            return
        self.doc['client_name'] = self.client_doc['name']
        self.doc['invoice_ref'] = self.client_doc.get('invoice_ref', '')
        self.doc['tax'] = round(self.doc['amount'] * self.tax, 1)
        self.doc['total'] = self.doc['amount'] + self.doc['tax']

    def render_pdf(self):
        total = self.doc['total']
        if self.home_country:
            invoice_country_iso = self.doc['address']['country_iso_alpha2']
            if invoice_country_iso and invoice_country_iso != self.home_country:  # no tax in bill
                total = self.doc['amount']
                self.doc['total'] = total
        tpl = self.jinja_env.get_template('invoice_tpl.html')
        self.invoice_fname = "{date}_CHF{total:.2f}_Nr{nr}_hosting-{name}_ta".format(
            date=self.doc['date'].strftime("%Y-%m-%d"),
            total=total,
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
                "service_by_client", key=self.client_id, include_docs=True):
            # view rows are plain dicts; MergedDoc reads doc.template_id
            service_doc = MergedDoc(self.db, AttributeDict(result['doc'])).doc
            service_def = Invoice.service_definitons[service_doc['service_type']]
            package = service_def['packages'][service_doc['package_type']]
            # always keep the package list price next to the effective price,
            # so the invoice shows whether the price was overwritten on the service
            package_price = float(package['price']) if 'price' in package else None
            own_price = service_doc.get('price')
            # MergedDoc turns an empty value into [] when the template has no
            # price either, so [] means "no own price" just like '' and None
            has_own_price = own_price not in (None, '', [])
            if not has_own_price:
                service_doc.pop('price', None)
            service_doc['price'] = get_default('price', service_doc, package)
            service_doc['package_price'] = package_price
            service_doc['price_overwritten'] = (
                has_own_price and service_doc['price'] != package_price
            )
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
            service_end_date = get_default(
                'end_date', service_doc, self.doc)
            if service_end_date > self.doc['end_date']:
                service_end_date = self.doc['end_date']
            service_doc['end_date'] = service_end_date
            # addons/included need the effective service period (dates above)
            service_doc['addons'] = self.add_addons(service_doc, service_def['addons'])
            service_doc['included'] = self.add_included(service_doc, package)
            doc_amount = self.add_amount(
                service_doc['price'], service_doc['start_date'], service_end_date)
            service_doc.update(doc_amount)
            if service_doc['total'] == 0.0 \
               and not service_doc['addons'] \
               and not service_doc['included']:
                pass
            else:
                service_type = service_doc['service_type']
                if service_type not in services:
                    services[service_type] = {'items': []}
                services[service_type]['items'].append(service_doc)
        if hasattr(self.settings, 'invoice_service_order'):
            servicesOrdered = OrderedDict()
            service_order = [s.strip() for s in self.settings.invoice_service_order.split(',')]
            for name in service_order:
                if name in services:
                    servicesOrdered[name] = services[name]
                    del services[name]
            if services:
                for k, v in services.items():
                    servicesOrdered[k] = v
            return servicesOrdered
        return services

    def set_item_period(self, item, service):
        """Set start_date/end_date on an addon or included item.

        desk_pad saves the item dates as 'startDate'/'endDate'. The item is
        billed inside the period of its service: it can not start before the
        service starts and can not end after the service ends. Returns True
        if the item is active in that period.
        """
        start_date = service['start_date']
        end_date = service['end_date']
        if 'startDate' in item:
            item_start_date = parse_date(item['startDate'], force_day='start')
            start_date = max(start_date, item_start_date)
        if 'endDate' in item:
            item_end_date = parse_date(item['endDate'])
            end_date = min(end_date, item_end_date)
        item['start_date'] = start_date
        item['end_date'] = end_date
        return start_date <= end_date

    def add_addons(self, service, sd_addons):
        addons = []
        addon_items = service.get('addon_service_items') or []
        for addon in addon_items:
            if not isinstance(addon, dict):
                raise TypeError(
                    f"addon {addon!r} of service {service.get('_id')} is not an object"
                )
            sd_addon = sd_addons[addon['itemType']]
            addon['price'] = get_default('price', addon, sd_addon)
            addon['title'] = get_default('title', addon, sd_addon)
            is_active = self.set_item_period(addon, service)
            if not is_active:
                continue
            addon.update(
                self.add_amount(addon['price'], addon['start_date'], addon['end_date'])
            )
            if addon['total'] != 0.0:
                addons.append(addon)
        if 'addon_service_items' in service:
            del service['addon_service_items']
        return addons

    def add_included(self, service, sd_package):
        included = []
        included_items = service.get('included_service_items') or []
        for item in included_items:
            sd_included = sd_package['included'][item['itemType']]
            item['title'] = get_default('title', item, sd_included)
            is_active = self.set_item_period(item, service)
            if not is_active:
                continue
            item['months'] = self.count_months(item['start_date'], item['end_date'])
            included.append(item)
        if 'included_service_items' in service:
            del service['included_service_items']
        return included

    def count_months(self, start_date, end_date):
        months = (
            (end_date.year - start_date.year) * 12 +
            (end_date.month - start_date.month) + 1
        )
        return months if months > 0 else 0

    def add_amount(self, price, start_date, end_date):
        item = {}
        item['months'] = self.count_months(start_date, end_date)
        item['amount'] = item['months'] * price
        item['tax'] = item['amount'] * self.tax
        item['total'] = item['amount'] + item['tax']
        self.doc['amount'] += item['amount']
        self.doc['tax'] += item['tax']
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
