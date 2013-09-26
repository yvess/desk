# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit import Server
from . import SettingsCommand


class InstallCommand(SettingsCommand):
    def set_settings(self, *args, **kwargs):
        super(InstallCommand, self).set_settings(*args, **kwargs)

    def setup_parser(self, subparsers, config_parser):
        install_parser = subparsers.add_parser(
            'install',
            help="""install the couchdb design docs""",
        )
        install_parser.add_argument(*config_parser['args'], **config_parser['kwargs'])

        return install_parser

    def run(self):
        server = Server(self.settings.couchdb_uri)
        db = server.get_or_create_db(self.settings.couchdb_db)
        loader = FileSystemDocsLoader('./_design')
        loader.sync(db, verbose=True)
