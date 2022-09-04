import tempfile
import re
from datetime import date
from datetime import timedelta
from pathlib import Path
from decimal import Decimal
from qrbill import QRBill
from cairosvg import svg2pdf
from PyPDF2 import PdfFileMerger
from datetime import datetime
from desk.utils import calc_esr_checksum


"""Add qrbill to invoice to pdf"""
class InvoiceQrBill(object):
    def __init__(self, settings, invoices_path):
        self.settings = settings
        self.invoices_path = invoices_path

    def add_qrbill(self, invoice_path):
        print('add_qrbill', invoice_path)
        invoice_name = invoice_path.name
        matches = re.match(r"(?P<date>\d{4}-\d{2}-\d{2})_CHF(?P<amount>\d+.\d+)_Nr(?P<invoice_nr>\d+).*", invoice_name).groupdict()
        amount=Decimal(matches['amount'])
        due_date=date(*[int(d) for d in matches['date'].split("-")]) + timedelta(days=30)
        invoice_nr = matches['invoice_nr']
        reference_number = f'{invoice_nr}{calc_esr_checksum(invoice_nr)}'
        reference_number = f'{reference_number:0>27}'

        # setup qrbill
        qrbill = QRBill(
            language='de',
            account=self.settings.invoice_qrbill_iban,
            reference_number=reference_number,
            amount=amount,
            currency='CHF',
            due_date=due_date.strftime("%Y-%m-%d"),
            additional_information=f'Rechnung Nr. {invoice_nr}',
            creditor=dict(
                name=self.settings.invoice_qrbill_name,
                street=self.settings.invoice_qrbill_street,
                house_num=self.settings.invoice_qrbill_house_num,
                pcode=self.settings.invoice_qrbill_pcode,
                city=self.settings.invoice_qrbill_city,
                country=self.settings.invoice_qrbill_country,
            )
        )

        # create save qrbill
        temp_svg = '/tmp/qrbilltemp.svg'
        temp_pdf = '/tmp/qrbilltemp.pdf'
        qrbill.as_svg(temp_svg, full_page=True)
        svg2pdf(file_obj=open(temp_svg, 'rb'), write_to=temp_pdf)

        invoices_merged_path = self.invoices_path / Path('qrbill')
        invoices_merged_path.mkdir(exist_ok=True)

        # add qrbill to invoice pdf
        invoice_merged_path = invoices_merged_path / invoice_name
        merger = PdfFileMerger()
        merger.append(str(invoice_path.resolve()))
        merger.append(temp_pdf)
        merger.write(str(invoice_merged_path.resolve()))
        merger.close()
