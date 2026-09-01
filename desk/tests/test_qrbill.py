import unittest
from pathlib import Path

from desk.plugin.invoice.qrbill import INVOICE_NAME_RE, InvoiceQrBill


class InvoiceNameTestCase(unittest.TestCase):
    def test_invoice_name_parses(self):
        match = INVOICE_NAME_RE.match("2026-09-01_CHF120.00_Nr55_hosting.pdf")
        self.assertEqual(match.group("amount"), "120.00")
        self.assertEqual(match.group("invoice_nr"), "55")

    def test_amount_needs_decimal_point(self):
        # regression: the unescaped dot accepted amounts Decimal() rejects
        self.assertIsNone(INVOICE_NAME_RE.match("2026-09-01_CHF120-50_Nr55.pdf"))

    def test_add_qrbill_skips_non_invoice_files(self):
        # regression: crashed with AttributeError on non-matching names
        qrbill = InvoiceQrBill(settings=None, invoices_path=Path("/nonexistent"))
        self.assertIsNone(qrbill.add_qrbill(Path("/nonexistent/notes.pdf")))


if __name__ == "__main__":
    unittest.main()
