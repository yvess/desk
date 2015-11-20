# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
from couchdbkit import Server
from desk.command import SettingsCommand
from desk.utils import get_crm_module
from desk.plugin.service import ImportServices, QueryServices


class ImportServiceCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        service_import_parser = subparsers.add_parser(
            'service-import',
            help="""import service data from ods""",
            description="Import service data ods, and load it into couch"
        )
        service_import_parser.add_argument(*config_parser['args'],
                                           **config_parser['kwargs'])
        service_import_parser.add_argument(
            "src", help="source of the ods file",
        )

        service_import_parser.add_argument(
            "-nr", "--nr-cols", type=int, dest="nr_cols", default=12,
            help="number of cols to read",
        )

        service_import_parser.add_argument(
            "-o", "--only-files", dest="only_files",
            action="store_true", default=False,
            help="only create files, don't upload to couchdb",
        )

        return service_import_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        self.todoyu = get_crm_module(self.settings)
        services = ImportServices(self.settings)
        services.create_files()


class QueryServiceCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        service_query_parser = subparsers.add_parser(
            'service-query',
            help="""query service data""",
            description="Query service data"
        )
        service_query_parser.add_argument(*config_parser['args'],
                                          **config_parser['kwargs'])
        service_query_parser.add_argument(
            "service", help="name of service to query"
        )

        service_query_parser.add_argument(
            "-p", "--packages", dest="service_packages", default=None,
            help="packages of services seperated by comma",
        )

        service_query_parser.add_argument(
            "-a", "--addons", dest="service_addons",  default=None,
            help="addons of services seperated by comma",
        )

        return service_query_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        services = QueryServices(self.settings)
        services.get_services()
