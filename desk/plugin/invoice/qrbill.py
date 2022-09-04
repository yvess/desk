import tempfile
import re
from datetime import date
from datetime import timedelta
from pathlib import Path
from decimal import Decimal
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from qrbill import QRBill
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
        with tempfile.TemporaryFile(encoding='utf-8', mode='r+') as temp:
            qrbill.as_svg(temp)
            temp.seek(0)
            qrbill_drawing = svg2rlg(temp)

        temp_path = '/tmp/qrbilltemp.pdf'
        invoices_merged_path = self.invoices_path / Path('qrbill')
        invoices_merged_path.mkdir(exist_ok=True)
        qrbill_canvas = canvas.Canvas(temp_path)
        renderPDF.draw(qrbill_drawing, qrbill_canvas, 0, 0)
        qrbill_canvas.save()

        # add qrbill to invoice pdf
        invoice_merged_path = invoices_merged_path / invoice_name
        merger = PdfFileMerger()
        merger.append(str(invoice_path.resolve()))
        merger.append(temp_path)
        merger.write(str(invoice_merged_path.resolve()))
        merger.close()
