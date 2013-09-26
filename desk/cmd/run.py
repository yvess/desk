# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import sys
import os
import time
import gevent
from couchdbkit import Server, Consumer
from couchdbkit.changes import ChangesStream
from restkit.conn import Connection
from socketpool.pool import ConnectionPool


sys.path.append("../")
from desk.utils import ObjectDict
from desk.plugin.base import Updater, MergedDoc
from desk.plugin import dns


class SettingsCommand(object):
    def set_settings(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings


class RunCommand(SettingsCommand):
    def set_settings(self, settings, *args, **kwargs):
        super(RunCommand, self).set_settings(settings, *args, **kwargs)
        if self.settings.worker_is_foreman:
            self.worker = Foreman(self.settings)
        else:
            self.worker = Worker(self.settings)

    def setup_parser(self, subparsers, config):
        run_parser = subparsers.add_parser(
            'run',
            help="""Worker is the agent for the desk plattform.
                           Command line switches overwrite config file settings""",
        )
        run_parser.add_argument(*config['args'], **config['kwargs'])
        run_parser.add_argument(
            "-o", "--run_once", dest="worker_daemon",
            help="run only once not as daemon", action="store_false", default=True
        )
        run_parser.add_argument(
            "-u", "--couchdb_uri", dest="couchdb_uri",
            metavar="URI", help="connection url of the server"
        )
        run_parser.add_argument(
            "-d", "--couchdb_db", dest="couchdb_db",
            metavar="NAME", help="database of the server"
        )
        run_parser.add_argument(
            "-f", "--foreman", dest="worker_is_foreman",
            help="be the foreman and a worker", action="store_true"
        )
        return run_parser

    def run(self):
        if self.settings.worker_daemon:
            self.worker.run()
        else:
            self.worker.run_once()


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
