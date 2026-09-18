import logging
import tempfile
import re
from datetime import date
from datetime import timedelta
from pathlib import Path
from decimal import Decimal
from qrbill import QRBill
from cairosvg import svg2pdf
from pypdf import PdfWriter
from desk.utils import calc_esr_checksum

logger = logging.getLogger(__name__)

INVOICE_NAME_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})_CHF(?P<amount>\d+\.\d+)_Nr(?P<invoice_nr>\d+).*"
)


class InvoiceQrBill(object):
    """Add qrbill to invoice to pdf"""

    def __init__(self, settings, invoices_path):
        self.settings = settings
        self.invoices_path = invoices_path

    def add_qrbill(self, invoice_path):
        logger.info('add_qrbill %s', invoice_path)
        invoice_name = invoice_path.name
        match = INVOICE_NAME_RE.match(invoice_name)
        if match is None:
            logger.warning('skip %s, no invoice filename', invoice_name)
            return
        matches = match.groupdict()
        amount = Decimal(matches['amount'])
        due_date = date(*[int(d) for d in matches['date'].split("-")]) + timedelta(days=30)
        invoice_nr = matches['invoice_nr']
        reference_number = f'{invoice_nr}{calc_esr_checksum(invoice_nr)}'
        reference_number = f'{reference_number:0>27}'

        # setup qrbill
        # qrbill >= 1.0 dropped due_date (removed from the Swiss QR standard),
        # so the payment deadline goes into additional_information instead
        qrbill = QRBill(
            language='de',
            account=self.settings.invoice_qrbill_iban,
            reference_number=reference_number,
            amount=amount,
            currency='CHF',
            additional_information=(
                f'Rechnung Nr. {invoice_nr}, '
                f'zahlbar bis {due_date.strftime("%d.%m.%Y")}'
            ),
            font_factor=0.9,
            creditor=dict(
                name=self.settings.invoice_qrbill_name,
                street=self.settings.invoice_qrbill_street,
                house_num=self.settings.invoice_qrbill_house_num,
                pcode=self.settings.invoice_qrbill_pcode,
                city=self.settings.invoice_qrbill_city,
                country=self.settings.invoice_qrbill_country,
            )
        )

        invoices_merged_path = self.invoices_path / Path('qrbill')
        invoices_merged_path.mkdir(exist_ok=True)
        invoice_merged_path = invoices_merged_path / invoice_name

        # create save qrbill
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_svg = Path(temp_dir) / 'qrbill.svg'
            temp_pdf = Path(temp_dir) / 'qrbill.pdf'
            qrbill.as_svg(str(temp_svg), full_page=True)
            with open(temp_svg, 'rb') as svg_file:
                svg2pdf(file_obj=svg_file, write_to=str(temp_pdf))

            # add qrbill to invoice pdf
            merger = PdfWriter()
            merger.append(str(invoice_path.resolve()))
            merger.append(str(temp_pdf))
            merger.write(str(invoice_merged_path.resolve()))
