# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import os
import time
import gevent
import logging
from couchdbkit import Server, Consumer
from couchdbkit.changes import ChangesStream
from restkit.conn import Connection
from socketpool.pool import ConnectionPool
from desk.utils import ObjectDict
from desk.plugin.base import Updater, MergedDoc
from desk.plugin import dns

DOC_TYPES = {
    'domain': dns
}


class Worker(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings
        self.pool = ConnectionPool(factory=Connection, backend="gevent")
        self.server = Server(uri=settings.couchdb_uri, pool=self.pool)
        self.db = self.server[settings.couchdb_db]
        self.provides = {}
        self._setup_worker()
        self.queue_kwargs = {
            'tasks_open': {
                'include_docs': True,
                'filter': self._cmd("tasks_open")
            }
        }

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

    def _process_tasks(self, tasks):
        provider_lookup = {}
        for (servcie_type, services) in self.provides.viewitems():
            for service in services:
                provider_lookup[service['name']] = servcie_type
        for task in tasks:
            if task['doc']['provider'] in provider_lookup:
                self._run_tasks(task_id=task['id'], docs=task['doc']['docs'])

    def _run_tasks(self, task_id, docs):
        successfull_tasks = []
        for doc_id in docs:
            doc = self.db.get(doc_id)
            successfull_tasks.append(self._do_task(doc))
        task_doc = self.db.get(task_id)
        if all(successfull_tasks):
            task_doc['state'] = 'done'
            self.db.save_doc(task_doc)
            logging.info("task done doc_id: %s" % task_doc['_id'])
        else:
            task_doc['state'] = 'failed'
            self.db.save_doc(task_doc)
            logging.info("task failed doc_id: %s" % task_doc['_id'])

    def _do_task(self, doc):
        if doc['type'] in self.provides:
            for service_settings in self.provides[doc['type']]:
                ServiceClass = None
                doc_type = doc['type']
                backend = service_settings['backend']
                backend_class = backend.title()
                try:
                    ServiceClass = getattr(
                        getattr(DOC_TYPES[doc_type], backend),
                        backend_class
                    )
                except AttributeError:
                    print("not found")
                if ServiceClass:
                    with ServiceClass(self.settings) as service:
                        updater = Updater(self.db, doc, service)
                        was_successfull = updater.do_task()
                        return was_successfull
        else:
            raise Exception("I doesn't provide the requested service")

    def _create_queue(self, item_function, run_once=False, **item_kwargs):
        if run_once is True:
            def queue_once():
                c = Consumer(self.db)
                items = c.fetch(since=0, **item_kwargs)['results']
                if items:
                    item_function(items)
            return queue_once
        else:
            def queue():
                with ChangesStream(
                    self.db, feed="continuous",
                    heartbeat=True, **item_kwargs
                ) as task_items:
                    item_function(task_items)
            return queue

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=False,
            **self.queue_kwargs['tasks_open']
        )
        gevent.joinall([gevent.spawn(queue_tasks_open)])

    def run_once(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=True,
            **self.queue_kwargs['tasks_open']
        )
        queue_tasks_open()


class Foreman(Worker):
    def __init__(self, *args, **kwargs):
        super(Foreman, self).__init__(*args, **kwargs)
        self.queue_kwargs['orders_open'] = {
            'include_docs': True, 'filter': self._cmd("orders_open")
        }
        self.queue_kwargs['tasks_done'] = {
            'include_docs': True, 'filter': self._cmd("tasks_done")
        }

    def _process_orders(self, orders):
        for order in orders:
            order_doc = order['doc']
            editor = order_doc['editor']
            providers = {}
            docs = []
            already_processed_orders = []
            for result in self.db.view(
                self._cmd("new_by_editor"), key=editor, include_docs=True
            ):
                if result['doc']['_id'] not in already_processed_orders:
                    doc = MergedDoc(self.db, result['doc']).doc
                    get_providers = getattr(
                        DOC_TYPES[doc['type']], 'get_providers'
                    )
                    for provider in (get_providers(doc)):
                        if provider in providers:
                            providers[provider].append(result['doc']['_id'])
                        else:
                            providers[provider] = [result['doc']['_id']]
                        providers[provider].sort()
                    docs.append(result['doc']['_id'])
            #order_doc['docs'] = docs
            order_doc['providers'] = providers
            already_processed_orders.append(order_doc['_id'])
            if order_doc['state'] != 'new_created_tasks' and self._create_tasks(providers=providers, order_id=order_doc["_id"]):
                order_doc['state'] = 'new_created_tasks'
            self.db.save_doc(order_doc)

    def _create_tasks(self, providers=None, order_id=None):
        logging.info("** creating tasks")
        current_time = time.mktime(time.localtime())
        created = False
        for provider in providers:
            created = True
            logging.info("** creating tasks for %s" % provider)
            task_id = "task-{}-{}".format(provider, self.server.next_uuid())  # int(time.mktime(current_time))
            doc = {
                "_id": task_id,
                "type": "task",
                "state": "new",
                "order_id": order_id,
                "docs": providers[provider],
                "provider": provider
            }
            self.db.save_doc(doc)
        return created

    def _update_order(self, tasks):
        for task in tasks:
            task_doc = task['doc']
            order_id = task_doc['order_id']
            order_doc = self.db.get(order_id)
            if not 'providers_done' in order_doc:
                order_doc['providers_done'] = []
            providers = order_doc['providers']
            providers_done = order_doc['providers_done']
            providers_done.append([task_doc['provider']])

            if all([p in providers for p in providers_done]):
            #if order['providers'] == providers_done:
                order_doc['state'] = 'done'
                update_docs_id = []
                [update_docs_id.extend(v) for v in providers_done.viewvalues()]
                bulk_docs = self.db.all_docs(
                    keys=update_docs_id, include_docs=True
                )
                update_docs = []
                for result in bulk_docs:
                    doc = result['doc']
                    doc['state'] = 'live'
                    update_docs.append(doc)
                self.db.bulk_save(update_docs)
            self.db.save_doc(order_doc)
            task_doc['state'] = 'done_checked'
            self.db.save_doc(order_doc)
            self.db.save_doc(task_doc)

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, one=False,
            **self.queue_kwargs['tasks_open']
        )
        queue_orders_open = self._create_queue(
            self._process_orders, one=False,
            **self.queue_kwargs['orders_open']
        )
        queue_tasks_done = self._create_queue(
            self._update_order, one=False,
            **self.queue_kwargs['tasks_done']
        )
        gevent.joinall([
            gevent.spawn(queue_orders_open),
            gevent.spawn(queue_tasks_open),
            gevent.spawn(queue_tasks_done)
        ])

    def run_once(self):
        queue_orders_open = self._create_queue(
            self._process_orders, run_once=True,
            **self.queue_kwargs['orders_open']
        )
        queue_orders_open()

        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=True,
            **self.queue_kwargs['tasks_open']
        )
        queue_tasks_open()

        queue_tasks_done = self._create_queue(
            self._update_order, run_once=True,
            **self.queue_kwargs['tasks_done']
        )
        queue_tasks_done()
