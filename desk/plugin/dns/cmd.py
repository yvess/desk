# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division

from os import mkdir, listdir, path, unlink
import sys
import shutil
import tempfile
from socket import gethostbyaddr
from desk.command import SettingsCommand
from desk.utils import CouchdbUploader, create_order_doc, auth_from_uri
from desk.plugin.dns.importer import IspmanDnsLDIF, IspmanClientLDIF
from desk.utils import FilesForCouch
from desk.plugin.dns.importer import DnsDocsProcessor


class ImportDnsCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        importdns_parser = subparsers.add_parser(
            'dns-import',
            help="""generate json files from ispman ldif export""",
            description="""Generate json files from ispman ldif export.
                    A folder `couch` is generated at the location of the ldif
                    file. The dns json files are in this folder."""
        )
        importdns_parser.add_argument(*config_parser['args'],
                                      **config_parser['kwargs'])
        importdns_parser.add_argument(
            "src",
            help="source of the ldif file with the DNS data, or the json dir",
        )
        importdns_parser.add_argument(
            "dest", default=None, nargs="?",
            help="dest of the json files with dns domains",
        )
        importdns_parser.add_argument(
            "-l", "--client-ldif", dest="src_client_ldif",
            metavar="CLIENT_LDIF",
            help="merge client data from ldif export"
        )
        importdns_parser.add_argument(
            "-t", "--templates", dest="template_ids", default=None,
            help="""doc ids of templates to check (comma separeted)
            only mx and namserver are used, first matched template is used"""
        )
        importdns_parser.add_argument(
            "-m", "--map", dest="map_id", default=None,
            help="""doc id of map to check for ip variables"""
        )
        importdns_parser.add_argument(
            "-n", "--no-import", dest="do_import", default=True,
            action="store_false",
            help="""only create json files no import into database"""
        )
        importdns_parser.add_argument(
            "-s", "--dest-at-src", dest="dest_at_src", default=False,
            action="store_true",
            help="""create dest at source file dir location"""
        )
        importdns_parser.add_argument(
            "-i", "--ips", dest="show_ips", default=False,
            action="store_true",
            help="""show all a record ips"""
        )

        return importdns_parser

    def create_files(self, dest=None, src=None):
        auth = auth_from_uri(self.settings.couchdb_uri)
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
                open(src, 'r'), sys.stdout, self.settings,
                clients_ldif=client_ldif, editor=auth[0]
            )
        else:
            dns_ldif = IspmanDnsLDIF(
                open(src, 'r'), sys.stdout, self.settings, editor=auth[0]
            )
        dns_ldif.parse()
        if self.settings.show_ips:
            for ip in dns_ldif.a_record_ips:
                try:
                    hostname = gethostbyaddr(ip)[0]
                except:
                    hostname = None
                print("ip:{} ({}), \ndomains:{}\n".format(
                    ip, hostname, dns_ldif.a_record_hosts[ip]))
        data = [[k, v] for k, v in dns_ldif.domains.iteritems()]
        docs_processor = DnsDocsProcessor(self.settings, data)
        docs_processor.process()
        json_files = FilesForCouch(data, dest, use_id_in_data=True)
        json_files.create()

    def run(self):
        src, dest = self.settings.src, self.settings.dest
        dest_at_src = self.settings.dest_at_src
        do_import = self.settings.do_import
        temp_dir = None
        if src.split("/")[-1].endswith(".ldif"):  # ldif as input file
            if dest_at_src:
                dest = "{}/couch".format(path.dirname(src))
                map(unlink, [path.join(dest, f) for f in listdir(dest)])
            else:
                temp_dir = tempfile.mkdtemp()
                dest = "{}/couch".format(temp_dir)
            if not path.isdir(dest):
                mkdir(dest)
            self.create_files(dest=dest, src=src)
            json_src = dest
        else:
            json_src = src  # for json dir as input files

        if do_import:
            couch_up = CouchdbUploader(
                path=json_src, couchdb_uri=self.settings.couchdb_uri,
                couchdb_db=self.settings.couchdb_db
            )
            for fname in listdir(json_src):
                couch_up.put(
                    data="@{}".format(fname),
                    doc_id=fname[:-5]
                )
            create_order_doc(couch_up)
        if temp_dir:
            shutil.rmtree(temp_dir)


class LdifPlainDnsCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        ldifplain_parser = subparsers.add_parser(
            'dns-ldifplain',
            help="""converts ldif files to plain text""",
            description="""Converts ldifs to plain text dns data for diff from dns-export"""
        )
        ldifplain_parser.add_argument(*config_parser['args'],
                                      **config_parser['kwargs'])
        ldifplain_parser.add_argument(
            "src",
            help="source of the ldif file with the DNS data",
        )

        ldifplain_parser.add_argument(
            "dest",
            help="dest of the plain text dns data file",
        )

        return ldifplain_parser

    def plain_text_records(self, dname, rtype, records):
        items = []
        if rtype in records:
            for record in records[rtype]:
                key_id, value_id = self.dns_ldif.structure_map[rtype]
                if rtype != 'mx':
                    key = record[key_id]
                    value = record[value_id]
                else:
                    key = "@"
                    value = record[key_id]
                if value == '.':
                    value = ''
                entry = u"{dname} {rtype} {key} {value}\n".format(
                    dname=dname, rtype=rtype.upper(), key=key, value=value
                )
                items.append(entry)
        return items

    def run(self):
        src, dest = self.settings.src, self.settings.dest
        output = []
        self.dns_ldif = IspmanDnsLDIF(
            open(src, 'r'), sys.stdout, self.settings
        )
        self.dns_ldif.parse()
        domains = [[k, v] for k, v in self.dns_ldif.domains.iteritems()]
        domains = sorted(domains, key=lambda x: x[0])
        for domain in domains:
            for rtype in ['a', 'aaaa', 'cname', 'mx', 'ns', 'txt', 'srv']:
                dname, records = domain[0], domain[1]
                if rtype == 'ns':
                    output.extend([u"%s NS @ %s\n" % (dname, n) for n in records['nameservers']])
                else:
                    output.extend(self.plain_text_records(dname, rtype, records))
        output.sort()
        with open(dest, 'w') as f:
            f.writelines(output)
