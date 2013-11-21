# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division

import os
import sys
import shutil
import tempfile
from desk.cmd import SettingsCommand
from desk.utils import CouchdbUploader, create_order_doc, auth_from_uri
from desk.plugin.dns.importer import IspmanDnsLDIF, IspmanClientLDIF
from desk.utils import FilesForCouch


class Ldif2JsonCommand(SettingsCommand):
    def setup_parser(self, subparsers):
        ldif2json_parser = subparsers.add_parser(
            'dns-ldif',
            help="""generate json files from ispman ldif export""",
            description="""Generate json files from ispman ldif export.
                    A folder `couch` is generated at the location of the ldif
                    file. The dns json files are in this folder."""
        )
        ldif2json_parser.add_argument(
            "src",
            help="source of the ldif file with the DNS data",
        )
        ldif2json_parser.add_argument(
            "-l", "--client-ldif", dest="src_client_ldif",
            metavar="CLIENT_LDIF",
            help="merge client data from ldif export"
        )

        return ldif2json_parser

    def run(self, dest=None, src=None):
        auth = auth_from_uri(self.settings.couchdb_uri)
        if not src:
            src = self.settings.src
        if not dest:
            dest = "{}/couch".format(os.path.dirname(self.settings.src))
            os.mkdir(dest)
        if hasattr(self.settings, 'src_client_ldif') and (
           self.settings.src_client_ldif):
            client_ldif = IspmanClientLDIF(
                open(self.settings.src_client_ldif, 'r'),
                sys.stdout, editor=auth[0]
            )
            client_ldif.parse()
            data = [(k, v) for k, v in client_ldif.clients.iteritems()]
            json_files = FilesForCouch(data, dest)
            json_files.create()
            dns_ldif = IspmanDnsLDIF(
                open(src, 'r'), sys.stdout,
                clients_ldif=client_ldif, editor=auth[0]
            )
        else:
            dns_ldif = IspmanDnsLDIF(
                open(src, 'r'), sys.stdout, editor=auth[0]
            )
        dns_ldif.parse()
        data = [(k, v) for k, v in dns_ldif.domains.iteritems()]
        json_files = FilesForCouch(data, dest, prefix="domain")
        json_files.create()


class ImportDnsCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        dns_import_parser = subparsers.add_parser(
            'dns-import',
            help="""import dns data from ispman""",
            description="Import dns data from ispman as ldif file, or json dir"
        )
        dns_import_parser.add_argument(*config_parser['args'],
                                       **config_parser['kwargs'])
        dns_import_parser.add_argument(
            "src", help="source of the ldif of json dir",
        )
        dns_import_parser.add_argument(
            "-l", "--client-ldif", dest="src_client_ldif",
            metavar="CLIENT_LDIF",
            help="merge client data from ldif export"
        )
        return dns_import_parser

    def run(self):
        temp_dir = None
        src = self.settings.src
        temp_dir = None
        if src.split("/")[-1].endswith(".ldif"):
            ldif2json = Ldif2JsonCommand()
            ldif2json.set_settings(self.settings)
            temp_dir = tempfile.mkdtemp()
            dest = "{}/couch".format(temp_dir)
            os.mkdir(dest)
            ldif2json.run(dest=dest, src=src)
            src = dest

        co = CouchdbUploader(
            path=src, couchdb_uri=self.settings.couchdb_uri,
            couchdb_db=self.settings.couchdb_db
        )
        for fname in os.listdir(src):
            co.put(
                data="@{}".format(fname),
                doc_id=fname[:-5]
            )

        if temp_dir:
            shutil.rmtree(temp_dir)
        create_order_doc(co)
