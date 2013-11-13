# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division

import codecs
from StringIO import StringIO
from desk.cmd import SettingsCommand
from couchdbkit import Server
from weasyprint import HTML
from jinja2 import Template
from desk.plugin.extcrm.todoyu import Todoyu


class CreateInvoicesCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        install_parser = subparsers.add_parser(
            'invoices-create',
            help="""Create invoices for recurring billing.""",
        )
        install_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        return install_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        todoyu = Todoyu(self.settings)
        server = Server(self.settings.couchdb_uri)
        db = server.get_db(self.settings.couchdb_db)

        for result in db.view(
            self._cmd("client_billable"), include_docs=True
        ):
            params = {}
            params.update(todoyu.get_address(result['doc']['crmId']))
            invoice_template_dir = self.settings.invoice_template_dir
            template_name = '%s/%s' % (invoice_template_dir, 'invoice.html')
            invoice_html = StringIO()
            with codecs.open(template_name, "r", "utf-8") as template:
                template_html = template.read()
                t = Template(template_html)
                invoice_html.write(t.render(**params).encode('utf-8'))
            invoice_html.seek(0)
            html = HTML(invoice_html, base_url=invoice_template_dir)
            html.write_pdf('/Users/yserrano/Desktop/test.pdf')
