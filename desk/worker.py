#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import sys
import os
from ConfigParser import SafeConfigParser
from ConfigParser import ParsingError
import argparse
from couchdbkit import Server, Consumer
from couchdbkit.changes import ChangesStream

sys.path.append("../")
from desk.utils import ObjectDict
from desk.plugin import dns
from desk.plugin.base import Updater, MergedDoc


class Worker(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.db = Server(uri=settings.couchdb_uri)[settings.couchdb_db]
        self.hostname = hostname
        self.provides = {}
        self.settings = settings
        self._setup_worker()

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def _setup_worker(self):
        worker_result = self.db.list(
            self._cmd("list_docs"),
            "worker", include_docs=True,
            keys=[self.hostname]
        )
        if worker_result:
            self.provides = worker_result[0]['provides']

    def _create_tasks_foreman(self, doc):
        service_type = (doc['type'])
        try:
            ServiceModule = getattr(globals()[service_type], '{}base'.format(service_type))
            print(ServiceModule)
            ServiceBaseClass = getattr(ServiceModule, '{}Provider'.format(service_type.capitalize()))
            print(ServiceBaseClass)
        except AttributeError:
            print("not found")
        providers = ServiceBaseClass().get_providers(doc=doc)
        print(providers)

    def _do_task(self, doc):
        if doc['type'] in self.provides:
            for service_settings in self.provides[doc['type']]:
                if 'server_type' in service_settings \
                and 'master' in service_settings['server_type'] \
                or not ('server_type' in service_settings):
                    ServiceClass = None
                    doc_type = doc['type']
                    backend = service_settings['backend']
                    backend_class = backend.title()
                    try:
                        ServiceClass = getattr(getattr(globals()[doc_type], backend), backend_class)
                    except AttributeError:
                        print("not found")
                    if ServiceClass:
                        with ServiceClass(self.settings) as service:
                            updater = Updater(self.db, doc, service)
                            updater.do_task()
        else:
            raise Exception("I doesn't provide the requested service")

    def _process_queue(self, queue):
        for notification in queue:
            # for foreman
            worker_is_foreman = self.settings.worker_is_foreman if hasattr(self.settings, 'worker_is_foreman') else False
            if worker_is_foreman and notification['doc']['sender'] == 'pad':
                for task in self.db.view(self._cmd("todo")):
                    doc = task['value']
                    doc = MergedDoc(self.db, self.db.get(doc['_id'])).doc
                    self._create_tasks_foreman(doc)
            # for workers
            if notification['doc']['sender'] == 'foreman' and \
            (notification['doc']['state'] != 'done' or notification['doc']['claimed'] != True):
                for task in self.db.view(self._cmd("todo")):
                    doc = task['value']
                    #self._do_task(doc)

    def run(self):
        with ChangesStream(self.db,
            feed="continuous", heartbeat=True,
            include_docs=True,
            filter=self._cmd("queue")):
            self._process_queue(queue)

    def once(self):
        c = Consumer(self.db)
        queue = c.fetch(since=0,
            include_docs=True,
            filter=self._cmd("queue"))['results']
        if queue:
            self._process_queue(queue)


def setup_parser():
    """create the command line parser / config file reader """

    defaults = {
        "couchdb_uri": "http://localhost:5984",
        "couchdb_db": "desk_drawer",
        "worker_daemon": True,
        "worker_is_foreman": False,
    }
    # first only parse the config file argument
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument("-c", "--config", dest="config",
        default="/etc/desk/worker.conf",
        help="path to the config file, default: /etc/desk/worker.conf",
        metavar="FILE"
    )
    args, remaining_args = conf_parser.parse_known_args()
    # load config files with settings, puts them into a dict format "section_option"
    if args.config:
        config = SafeConfigParser()
        if not config.read([args.config]):
            print("Can't open file '{}'".format(args.config))
            sys.exit(0)
        else:
            for section in ['couchdb', 'powerdns']:  # put in here all your sections
                defaults.update(
                    {'{}_{}'.format(section, k):v for k, v in config.items(section)}
                )
    # parse all other arguments
    parser = argparse.ArgumentParser(
        parents=[conf_parser],
        description="""Worker is the agent for the desk plattform.
                       Command line switches overwrite config file settings""",
    )
    parser.set_defaults(**defaults)
    parser.add_argument("-o", "--once", dest="worker_daemon",
        help="run only once not as daemon", action="store_false", default=True)
    parser.add_argument("-u", "--couchdb_uri", dest="couchdb_uri",
        metavar="URI", help="connection url of the server")
    parser.add_argument("-d", "--couchdb_db", dest="couchdb_db",
        metavar="NAME", help="database of the server")
    parser.add_argument("-f", "--foreman", dest="worker_is_foreman",
        help="be the foreman and a worker", action="store_true", default=False)

    args = parser.parse_args(remaining_args)

    return args

if __name__ == "__main__":
    settings = setup_parser()
    worker = Worker(settings)
    if settings.worker_daemon:
        worker.run()
    else:
        worker.once()
