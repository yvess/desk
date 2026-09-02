from desk.command import SettingsCommandDb
from desk.plugin.service import QueryServices


class QueryServiceCommand(SettingsCommandDb):
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

        service_query_parser.add_argument(
            "-i", "--included_items", dest="included_items", default=None,
            help="show value of included_items",
        )

        service_query_parser.add_argument(
            "-b", "--onlybillable", dest="only_billable", default=False,
            action="store_true",
            help="only show billable clients",
        )

        return service_query_parser

    def run(self):
        services = QueryServices(self.settings, self.db)
        services.query()
