#!/usr/bin/env python3

import sys
import re
import signal
from configparser import ConfigParser
import argparse
import os
from collections import OrderedDict
from desk.command import InstallDbCommand, InstallWorkerCommand
from desk.command import WorkerCommand, MigrateCommand
is_foreman = True if os.environ.get('WORKER_TYPE', 'worker') == 'foreman' else False
from desk.plugin.dns.cmd_powerdns import PowerdnsExportCommand, PowerdnsRebuildCommand
if is_foreman:
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


def to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


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
        self.parsers = []
        self.commands_map = {}

        self.setup_commands()
        self.merge_configfile()
        self.update_parser()

    def setup_commands(self):
        self.worker_cmd = WorkerCommand()
        self.worker_parser = self.worker_cmd.setup_parser(
            self.subparsers, CONFIG_PARSER, VERBOSE_PARSER
        )
        self.parsers.append(self.worker_parser)

        self.commands = OrderedDict([
            ('install-db', InstallDbCommand),
            ('install-worker', InstallWorkerCommand),
            ('migrate', MigrateCommand),
            ('dns-export-powerdns', PowerdnsExportCommand),
            ('dns-rebuild-powerdns', PowerdnsRebuildCommand),
            ('service-query', QueryServiceCommand),
        ])
        if is_foreman:
            self.commands['invoices-create'] = CreateInvoicesCommand

        for command_name, command in list(self.commands.items()):
            name_snake = to_snake_case(command.__name__)
            command_instance = command()
            command_parser = command_instance.setup_parser(
                self.subparsers, CONFIG_PARSER
            )
            self.commands[command_name] = command_instance

            setattr(self, '%s_cmd' % name_snake, command_instance)
            setattr(self, '%s_parser' % name_snake, command_parser)
            self.parsers.append(command_parser)

    def merge_configfile(self):
        if self.pass_args:
            args = self.main_parser.parse_args(self.pass_args)
        else:
            args = self.main_parser.parse_args()

        # load config files with settings
        # puts them into a dict format "section_option"
        merged_defaults = DEFAULTS.copy()
        if hasattr(args, 'config') and args.config:
            config = ConfigParser()
            with open(args.config, 'r') as file:
                config.read_file(file)
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
        for parser in self.parsers:
            parser.set_defaults(**self.merged_defaults)
        if self.pass_args:
            self.settings = self.main_parser.parse_args(self.pass_args)
        else:
            self.settings = self.main_parser.parse_args()


def signal_handler(signum, frame):
    if signum == signal.SIGTERM or signum == signal.SIGHUP:
        sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

if __name__ == "__main__":
    worker = SetupWorkerParser()
    if worker.settings.command == 'run':
        worker.worker_cmd.set_settings(worker.settings)
        worker.worker_cmd.run()
    elif worker.settings.command in worker.commands:
        current_command = worker.commands[worker.settings.command]
        current_command.set_settings(worker.settings)
        current_command.run()
