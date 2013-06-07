#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import sys
import os
from ConfigParser import SafeConfigParser
from ConfigParser import ParsingError
import argparse
from gevent import monkey; monkey.patch_all()
import gevent
from couchdbkit import Server, Consumer
from couchdbkit.changes import ChangesStream
from restkit.conn import Connection
from socketpool.pool import ConnectionPool


sys.path.append("../")
from desk.utils import ObjectDict
from desk.plugin import dns
from desk.plugin.base import Updater, MergedDoc


class Worker(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.pool = ConnectionPool(factory=Connection, backend="gevent")
        self.db = Server(uri=settings.couchdb_uri, pool=self.pool)[settings.couchdb_db]
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

    def _create_tasks(self, doc):
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

    # def _process_order(self, orders):
    #     # for foreman
    #     if is_foreman:
    #         for task in self.db.view(self._cmd("todo")):
    #             doc = task['value']
    #             doc = MergedDoc(self.db, self.db.get(doc['_id'])).doc
    #             self._create_tasks(doc)
    #     # for workers
    #     if notification['doc']['state'] != 'done' or notification['doc']['claimed'] != True:
    #         for task in self.db.view(self._cmd("todo")):
    #             doc = task['value']
    #             #self._do_task(doc)

    def _process_orders(self, orders):
        for order in orders:
            print('order')
        # for task in self.db.view(self._cmd("todo")):
        #     doc = task['value']
        #     doc = MergedDoc(self.db, self.db.get(doc['_id'])).doc
        #     self._create_tasks(doc)

    def _process_tasks(self, tasks):
        for task in tasks:
            print('tasks')

    def get_queues(self, is_foreman=False):
        def orders_queue():
            with ChangesStream(self.db, feed="continuous", heartbeat=True,
                include_docs=True, filter=self._cmd("orders_open")) as orders:
                self._process_orders(orders)

        def tasks_queue():
            with ChangesStream(self.db, feed="continuous", heartbeat=True,
                include_docs=True, filter=self._cmd("tasks_open")) as tasks:
                self._process_tasks(tasks)

        queues = [gevent.spawn(orders_queue), gevent.spawn(tasks_queue)] if is_foreman else [gevent.spawn(tasks_queue)]
        return queues

    def _check_is_foreman(self):
        if hasattr(self.settings, 'worker_is_foreman'):
            return self.settings.worker_is_foreman
        else:
            return False

    def run(self):
        is_foreman = self._check_is_foreman()
        queues = self.get_queues(is_foreman=is_foreman)
        gevent.joinall(queues)

    def once(self):
        c = Consumer(self.db)
        orders = c.fetch(since=0,
            include_docs=True,
            filter=self._cmd("orders_open"))['results']
        tasks = c.fetch(since=0,
            include_docs=True,
            filter=self._cmd("tasks_open"))['results']
        if orders:
            self._process_orders(orders)
        if tasks:
            self._process_orders(orders)


def setup_parser():
    """create the command line parser / config file reader """

    defaults = {
        "couchdb_uri": "http://localhost:5984",
        "couchdb_db": "desk_drawer",
        "worker_daemon": True,
        "worker_is_foreman": False,
    }
    boolean_types = ['worker_daemon', 'worker_is_foreman']
    conf_sections = ['couchdb', 'powerdns', 'worker']
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
            for section in conf_sections:  # put in here all your sections
                conf_section = {}
                for k, v in config.items(section):
                    section_prop = '{}_{}'.format(section, k)
                    if section_prop in boolean_types:
                        conf_section[section_prop] = config.getboolean(section, k)
                    else:
                        conf_section[section_prop] = config.get(section, k)
                defaults.update(conf_section)
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
        help="be the foreman and a worker", action="store_true")

    settings = parser.parse_args(remaining_args)

    return settings

if __name__ == "__main__":
    settings = setup_parser()
    worker = Worker(settings)
    if settings.worker_daemon:
        worker.run()
    else:
        worker.once()
