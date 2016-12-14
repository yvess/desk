# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
import sys

from desk.command import SettingsCommand, SettingsCommandDb
from desk.utils import ObjectDict
from desk.plugin.dns.powerdns import Powerdns
from desk.plugin.base import MergedDoc


class PowerdnsExportCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        export_powerdns_parser = subparsers.add_parser(
            'dns-export-powerdns',
            help="""converts powerdns data to plain text""",
            description="""Converts plain text dns data for diff from ldif plaintext"""
        )
        export_powerdns_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        export_powerdns_parser.add_argument(
            "db",
            help="""path to the sqlite database"""
        )

        export_powerdns_parser.add_argument(
            "dest",
            help="dest of the plain text dns data file",
        )

        return export_powerdns_parser

    def run(self):
        conf = {
            'powerdns_backend': "sqlite",
            'powerdns_db': self.settings.db
        }
        pdns = Powerdns(ObjectDict(**conf))
        dest = self.settings.dest
        output = []

        domains = pdns.get_domains()

        for domain in domains:
            records = pdns.get_records(domain)
            for rtype in records:
                for record in records[rtype]:
                    entry = u"{dname} {rtype} {key} {value}\n".format(
                            dname=domain, rtype=rtype.upper(),
                            key=record[0], value=record[1]
                    )
                    output.append(entry)
        output.sort()
        with open(dest, 'w') as f:
            f.writelines(output)


class PowerdnsRebuildCommand(SettingsCommandDb):
    def setup_parser(self, subparsers, config_parser):
        rebuild_powerdns_parser = subparsers.add_parser(
            'dns-rebuild-powerdns',
            help="""rebuilds the dns entries for a domain""",
            description="""rebuilds the dns entries for a domain, or all domains"""
        )
        rebuild_powerdns_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        rebuild_powerdns_parser.add_argument(
            "db",
            help="""path to the sqlite database"""
        )

        rebuild_powerdns_parser.add_argument(
            "target", default=None, nargs="?",
            help="name of the domain to process, or nothing for all domains (needs confirmation)",
        )

        rebuild_powerdns_parser.add_argument(
            "-d", "--only-delete", dest="only_delete",
            action="store_true", default=False,
            help="""only delete all domains, no recreate"""
        )

        return rebuild_powerdns_parser

    def _rebuild(self, domain, pre_delete=True):
        unmerged_doc = self.db.view(
            self._cmd("domain_by_name"), include_docs=True, key=domain
        ).one()['doc']
        doc = MergedDoc(self.db, unmerged_doc).doc
        self.pdns.doc = doc
        if pre_delete:
            self.pdns.set_domain(domain)
            last_serial = self.pdns.get_soa_serial()
            self.pdns.del_domain(domain)
            self.pdns.create()
            self.pdns.update_soa(serial=last_serial)
        else:
            self.pdns.create()
            self.pdns.update_soa(serial=None)

    def run(self):
        conf = {
            'powerdns_backend': "sqlite",
            'powerdns_db': self.settings.db
        }
        self.pdns = Powerdns(ObjectDict(**conf))
        lookup_map_doc = self.db.get(self.pdns.map_doc_id)
        self.pdns.set_lookup_map(lookup_map_doc)

        domains = []
        for domain in self.db.view(
            self._cmd("domain_by_name"), include_docs=True
        ):
            domains.append(domain['key'])
        if self.settings.target:
            self._rebuild(self.settings.target)
        else:
            sys.stdout.write("Do you really want to procced and rebuild all domains? yes/no: ")
            choice = raw_input().lower()
            if choice == 'yes':
                self.pdns.del_domains()
                if not self.settings.only_delete:
                    for domain in domains:
                        print("adding:", domain)
                        self._rebuild(domain, pre_delete=False)
                else:
                    print("only deletion of data was requestd")
