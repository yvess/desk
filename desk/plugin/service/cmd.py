# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division
from couchdbkit import Server
from desk.cmd import SettingsCommand
from desk.plugin.extcrm.todoyu import Todoyu
from desk.plugin.service.importer import ImportServices


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
            "-nr", "--nr-cols", type=int, dest="nr_cols", default=17,
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
        self.todoyu = Todoyu(self.settings)
        self.nr_cols = self.settings.nr_cols
        import_service = ImportServices()
        import_service.init_couch()
        import_service.init_spreadsheet()
        import_service.create_docs()
        clients_extcrm_ids = {}
        import_service.create_servies_files()
