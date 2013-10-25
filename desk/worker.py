#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

from gevent import monkey; monkey.patch_all()
import sys
from ConfigParser import SafeConfigParser
import argparse
from desk.cmd import InstallDbCommand, InstallWorkerCommand, WorkerCommand
from desk.plugin.dns.cmd import Ldif2JsonCommand, ImportDnsCommand


DEFAULTS = {
    "couchdb_uri": "http://localhost:5984",
    "couchdb_db": "desk_drawer",
    "worker_daemon": True,
    "worker_is_foreman": False,
}

CONFIG_PARSER = {
    'args': ["-c", "--config"],
    'kwargs': {
        'dest': "config",
        'default': "/etc/desk/worker.conf",
        'help': "path to the config file, default: /etc/desk/worker.conf",
        'metavar': "FILE"
    }
}

VERBOSE_PARSER = {
    'args': ["-v", "--verbose"],
    'kwargs': {
        'dest': "loglevel",
        'action': "store_const",
        'default': "warning",
        'const': "info",
        'help': "set the loglevel",
    }
}

BOOLEAN_TYPES = ['worker_daemon', 'worker_is_foreman']
CONF_SECTIONS = ['couchdb', 'powerdns', 'worker']


class SetupWorkerParser(object):
    def __init__(self, pass_args=None):
        """create the command line parser / config file reader """

        self.main_parser = argparse.ArgumentParser()
        self.pass_args = pass_args
        self.subparsers = self.main_parser.add_subparsers(
            dest='command',
            title="subcommands",
            description="available subcommands",
            help="all commands"
        )

        self.setup_commands()
        self.merge_configfile()
        self.update_parser()

    def setup_commands(self):
        self.worker_cmd = WorkerCommand()
        self.worker_parser = self.worker_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER, VERBOSE_PARSER
        )

        self.install_db_cmd = InstallDbCommand()
        self.install_db_parser = self.install_db_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.install_worker_cmd = InstallWorkerCommand()
        self.install_worker_parser = self.install_worker_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.dns_ldif2json_cmd = Ldif2JsonCommand()
        self.dns_ldif2json_parser = self.dns_ldif2json_cmd.setup_parser(
            self.subparsers
        )

        self.dns_import_cmd = ImportDnsCommand()
        self.dns_import_parser = self.dns_import_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

    def merge_configfile(self):
        if self.pass_args:
            args = self.main_parser.parse_args(self.pass_args)
        else:
            args = self.main_parser.parse_args()

        # load config files with settings
        # puts them into a dict format "section_option"
        merged_defaults = DEFAULTS.copy()
        if hasattr(args, 'config') and args.config:
            config = SafeConfigParser()
            if not config.read([args.config]):
                print("Can't open file '{}'".format(args.config))
                sys.exit(0)
            else:
                for section in CONF_SECTIONS:
                    conf = {}
                    if config.has_section(section):
                        for k, v in config.items(section):
                            prop = '{}_{}'.format(section, k)
                            if prop in BOOLEAN_TYPES:
                                conf[prop] = config.getboolean(section, k)
                            else:
                                conf[prop] = config.get(section, k)
                    merged_defaults.update(conf)
        self.merged_defaults = merged_defaults

    def update_parser(self):
        self.worker_parser.set_defaults(**self.merged_defaults)
        self.install_db_parser.set_defaults(**self.merged_defaults)
        self.install_worker_parser.set_defaults(**self.merged_defaults)
        self.dns_ldif2json_parser.set_defaults(**self.merged_defaults)
        self.dns_import_parser.set_defaults(**self.merged_defaults)
        if self.pass_args:
            self.settings = self.main_parser.parse_args(self.pass_args)
        else:
            self.settings = self.main_parser.parse_args()

if __name__ == "__main__":
    worker = SetupWorkerParser()
    if worker.settings.command == 'run':
        worker.worker_cmd.set_settings(worker.settings)
        worker.worker_cmd.run()
    elif worker.settings.command == 'install-db':
        worker.install_db_cmd.set_settings(worker.settings)
        worker.install_db_cmd.run()
    elif worker.settings.command == 'install-worker':
        worker.install_worker_cmd.set_settings(worker.settings)
        worker.install_worker_cmd.run()
    elif worker.settings.command == 'dns-ldif':
        worker.dns_ldif2json_cmd.set_settings(worker.settings)
        worker.dns_ldif2json_cmd.run()
    elif worker.settings.command == 'dns-import':
        worker.dns_import_cmd.set_settings(worker.settings)
        worker.dns_import_cmd.run()
