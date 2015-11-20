#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

from gevent import monkey; monkey.patch_all()
import sys
import os
import signal
from ConfigParser import SafeConfigParser
import argparse
import codecs
from desk.command import InstallDbCommand, InstallWorkerCommand
from desk.command import WorkerCommand, UploadJsonCommand
from desk.plugin.dns.cmd import ImportDnsCommand
from desk.plugin.invoice.cmd import CreateInvoicesCommand
from desk.plugin.service.cmd import ImportServiceCommand, QueryServiceCommand


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
CONF_SECTIONS = ['couchdb', 'powerdns', 'worker', 'todoyu',
                 'invoice', 'service_web', 'service_email']


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

        self.upload_json_cmd = UploadJsonCommand()
        self.upload_json_parser = self.upload_json_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.dns_import_cmd = ImportDnsCommand()
        self.dns_import_parser = self.dns_import_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.invoices_create_cmd = CreateInvoicesCommand()
        self.invoices_create_parser = self.invoices_create_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.service_import_cmd = ImportServiceCommand()
        self.service_import_parser = self.service_import_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER
        )

        self.service_query_cmd = QueryServiceCommand()
        self.service_query_parser = self.service_query_cmd.setup_parser(
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
            config.readfp(codecs.open(args.config, "r", "utf8"))
            if not config:
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
        self.upload_json_parser.set_defaults(**self.merged_defaults)
        self.dns_import_parser.set_defaults(**self.merged_defaults)
        self.invoices_create_parser.set_defaults(**self.merged_defaults)
        self.service_import_parser.set_defaults(**self.merged_defaults)
        self.service_query_parser.set_defaults(**self.merged_defaults)
        if self.pass_args:
            self.settings = self.main_parser.parse_args(self.pass_args)
        else:
            self.settings = self.main_parser.parse_args()


def signal_handler(signum, frame):
    if signum == signal.SIGHUP:
        # restart program
        python = sys.executable
        os.execl(python, python, * sys.argv)

signal.signal(signal.SIGHUP, signal_handler)

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
    elif worker.settings.command == 'upload-json':
        worker.upload_json_cmd.set_settings(worker.settings)
        worker.upload_json_cmd.run()
    elif worker.settings.command == 'dns-import':
        worker.dns_import_cmd.set_settings(worker.settings)
        worker.dns_import_cmd.run()
    elif worker.settings.command == 'invoices-create':
        worker.invoices_create_cmd.set_settings(worker.settings)
        worker.invoices_create_cmd.run()
    elif worker.settings.command == 'service-import':
        worker.service_import_cmd.set_settings(worker.settings)
        worker.service_import_cmd.run()
    elif worker.settings.command == 'service-query':
        worker.service_query_cmd.set_settings(worker.settings)
        worker.service_query_cmd.run()
