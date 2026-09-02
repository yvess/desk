import sys

from desk.command import SettingsCommand, SettingsCommandDb
from desk.utils import AttributeDict, get_doc
from desk.plugin.dns.dnsbase import DnsValidator
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
            "dest",
            help="dest of the plain text dns data file",
        )

        return export_powerdns_parser

    def run(self):
        pdns = Powerdns(self.settings)
        dest = self.settings.dest
        output = []

        domains = pdns.get_domains()

        for domain in domains:
            records = pdns.get_records(domain)
            for rtype in records:
                for record in records[rtype]:
                    entry = "{dname} {rtype} {key} {value}\n".format(
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
            "target", default=None, nargs="?",
            help="name of the domain to process, or nothing for all domains (needs confirmation)",
        )

        rebuild_powerdns_parser.add_argument(
            "-d", "--only-delete", dest="only_delete",
            action="store_true", default=False,
            help="""only delete all domains, no recreate"""
        )

        return rebuild_powerdns_parser

    def _rebuild(self, domain):
        # view rows are plain dicts; MergedDoc reads doc.template_id
        rows = self.db.view("domain_by_name", include_docs=True, key=domain)
        if not rows:
            raise LookupError(f"domain {domain} not found in {self.db.db_name}")
        doc = MergedDoc(self.db, AttributeDict(rows[0]['doc'])).doc
        self.pdns.doc = doc
        # create() syncs an existing zone rather than recreating it, so the
        # SOA serial keeps climbing instead of restarting
        self.pdns.create()

    def run(self):
        self.pdns = Powerdns(self.settings)
        # httpx does not raise on a 404, a missing map doc must abort here
        map_response = self.db.get(self.pdns.map_doc_id)
        map_response.raise_for_status()
        self.pdns.set_lookup_map(get_doc(map_response))

        domains = [
            row['key'] for row in self.db.view("domain_by_name")
        ]
        if self.settings.target:
            self._rebuild(self.settings.target)
        else:
            sys.stdout.write("Do you really want to procced and rebuild all domains? yes/no: ")
            choice = input().lower()
            if choice == 'yes':
                self.pdns.del_domains()
                if not self.settings.only_delete:
                    for domain in domains:
                        print("adding:", domain)
                        self._rebuild(domain)
                else:
                    print("only deletion of data was requestd")


class DnsCheckCommand(SettingsCommandDb):
    """Read the zones back over DNS and compare them with CouchDB.

    The worker writes zones through the PowerDNS API; this asks the nameservers
    the documents name whether they actually answer with what the document
    says. It is the only check that covers the whole path, and it is what the
    old integration suite used to assert.
    """

    def setup_parser(self, subparsers, config_parser):
        check_parser = subparsers.add_parser(
            'dns-check',
            help="""check the nameservers against the domain documents""",
            description="""Queries every nameserver a domain names and reports
            whether the answers match the document."""
        )
        check_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )
        check_parser.add_argument(
            "target", default=None, nargs="?",
            help="name of the domain to check, or nothing for all domains",
        )
        check_parser.add_argument(
            "-n", "--nameserver", dest="nameservers",
            action="append", default=[], metavar="NAME=ADDRESS",
            help="""resolve a nameserver name to this address instead of
                 looking it up (repeatable)""",
        )
        return check_parser

    def run(self):
        lookup = dict(
            entry.split('=', 1) for entry in self.settings.nameservers
        ) or None
        map_response = self.db.get(DnsValidator.map_doc_id)
        if map_response.status_code != 404:
            map_response.raise_for_status()
            DnsValidator.lookup_map = get_doc(map_response)['map']

        domains = [self.settings.target] if self.settings.target else [
            row['key'] for row in self.db.view("domain_by_name")
        ]
        failed = []
        for domain in domains:
            rows = self.db.view(
                "domain_by_name", include_docs=True, key=domain
            )
            if not rows:
                raise LookupError(
                    f"domain {domain} not found in {self.db.db_name}"
                )
            doc = MergedDoc(self.db, AttributeDict(rows[0]['doc'])).doc
            valid = DnsValidator(doc, lookup=lookup).do_check()
            print("{} {}".format("ok  " if valid else "FAIL", domain))
            if not valid:
                failed.append(domain)
        print("{}/{} zones match".format(
            len(domains) - len(failed), len(domains)
        ))
        return not failed
