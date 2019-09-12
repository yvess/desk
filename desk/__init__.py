import os
import sys
import socket
import time
import logging
import json
import asyncio
from desk.utils import ObjectDict, CouchDBSession, CouchDBSessionAsync, AttributeDict
from desk.utils import get_rows, decode_json, encode_json, get_doc, get_key
from desk.plugin.base import Updater, MergedDoc
from desk.plugin import dns

__version__ = '0.1'

DOC_TYPES = {
    'domain': dns
}
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("areq")
logging.getLogger("chardet.charsetprober").disabled = True

class Worker(object):
    def __init__(self, settings, hostname=socket.getfqdn()):
        if isinstance(settings, dict):
            self.settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings
        self.db_name = self.settings.couchdb_db
        self.db = CouchDBSession.db(settings.couchdb_uri, db_name=settings.couchdb_db)
        self.db_async = CouchDBSessionAsync.db(settings.couchdb_uri, db_name=settings.couchdb_db)
        self.db_design = CouchDBSession.db_design(settings.couchdb_uri, db_name=settings.couchdb_db)
        self.provides = {}
        self._setup_worker()
        self.queue_kwargs = {
            'tasks_open': {
                'include_docs': 'true',
                'filter': f'{self.db_name}/tasks_open'
            }
        }

        self.logger = logging.getLogger(__name__)

    def _setup_worker(self):
        worker_result = self.db_design.get('_list/list_docs/worker', params=dict(
            include_docs='true', keys=f'["{self.hostname}"]'
        ))
        worker_result.raise_for_status()
        if worker_result:
            self.provides = worker_result.json()[0]['provides']

    def _process_task(self, task):
        self.logger.info("ready for processing tasks")
        provider_lookup = {}
        task = AttributeDict(task)
        for (service_type, services) in self.provides.items():
            for service in services:
                provider_lookup[service['name']] = service_type

            if task.doc.provider in provider_lookup:
                self._run_tasks(task_id=task.id, docs=task.doc.docs)

    def _run_tasks(self, task_id, docs):
        successfull_tasks = []
        for doc_id in docs:
            doc = get_doc(self.db.get(doc_id))
            self.logger.info("do task %s" % task_id)
            was_successfull = self._do_task(doc)
            successfull_tasks.append(was_successfull)
        task_doc = get_doc(self.db.get(task_id))
        if all(successfull_tasks):
            task_doc.state = 'done'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            self.logger.info("task done doc_id: %s" % task_doc['_id'])
        else:
            task_doc.state = 'error'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            self.logger.info("task error doc_id: %s" % task_doc['_id'])

    def _do_task(self, doc):
        if doc.type in self.provides:
            for service_settings in self.provides[doc.type]:
                ServiceClass = None
                doc_type = doc.type
                backend = service_settings['backend']
                backend_class = backend.title()
                try:
                    ServiceClass = getattr(
                        getattr(DOC_TYPES[doc_type], backend),
                        backend_class
                    )
                except AttributeError:
                    self.logger.error("not found: %s" % doc._id)
                if ServiceClass:
                    with ServiceClass(self.settings) as service:
                        updater = Updater(self.db, doc, service)
                        was_successfull = updater.do_task()
                        return was_successfull
        else:
            self.logger.error("I doesn't provide the requested service")
            raise Exception("I doesn't provide the requested service")

    def _create_queue(self, item_function, run_once=False, **item_kwargs):
        if run_once is True:
            def queue_once():
                params = dict(
                    feed='continuous', heartbeat="true", since=0,
                    timeout=50000
                )
                params.update(item_kwargs)
                r = self.db.get('_changes', stream=True, params=params)
                for content in r.iter_content(chunk_size=None):
                    for line in content.decode('utf8').split('\n'):
                        if line:
                            logger.info(f'once line {line}')
                            item_function(decode_json(line))
                # c = Consumer(self.db)
                # items = c.fetch(since=0, **item_kwargs)['results']
                # if items:
                #     item_function(items)
            return queue_once
        else:
            async def queue():
                params = dict(
                    feed='continuous', heartbeat="true", since="now",
                    timeout=50000
                )
                params.update(item_kwargs)
                r = await self.db_async.get('_changes', stream=True, params=params)
                for content in r.iter_content(chunk_size=None):
                    for line in content.decode('utf8').split('\n'):
                        if line:
                            logger.info(f'once line {line}')
                            item_function(decode_json(line))
                        # print(line)
                        # with ChangesStream(
                        #     self.db, feed="continuous",
                        #     heartbeat=True, **item_kwargs
                        # ) as task_items:
                        #     item_function(task_items)
            return queue

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_task, run_once=False,
            **self.queue_kwargs['tasks_open']
        )

        loop = asyncio.new_event_loop()
        tasks_open = loop.create_task(queue_tasks_open())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def run_once(self):
        queue_tasks_open = self._create_queue(
            self._process_task, run_once=True,
            **self.queue_kwargs['tasks_open']
        )
        queue_tasks_open()


class Foreman(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_kwargs['orders_open'] = {
            'include_docs': 'true', 'filter': f'{self.db_name}/orders_open'
        }
        self.queue_kwargs['tasks_done'] = {
            'include_docs': 'true', 'filter': f'{self.db_name}/tasks_done'
        }

    def _process_orders(self, orders):
        self.logger.info("ready for processing orders")
        if not isinstance(orders, list):
            orders = [orders]
        for order in orders:
            providers, docs = {}, []
            already_processed_orders = []
            items = get_rows(self.db_design.get('_view/new_by_editor', params=dict(include_docs='true')))
            order_doc = AttributeDict(order['doc'])
            for item in map(AttributeDict, items):
                if item.doc._id not in already_processed_orders:
                    doc = MergedDoc(self.db, item.doc, cache_key=order_doc._id).doc
                    get_providers = getattr(
                        DOC_TYPES[doc.type], 'get_providers'
                    )
                    doc_providers = get_providers(doc)
                    for provider in doc_providers:
                        if provider in providers:
                            providers[provider].append(item.doc._id)
                        else:
                            providers[provider] = [item.doc._id]
                        providers[provider].sort()
                    docs.append(item.doc._id)

            order_doc.providers = providers
            if self._create_tasks(providers=providers, order_id=order_doc._id):
                order_doc.state = 'new_created_tasks'
            if order_doc.state == 'new':
                if providers:
                    order_doc.state = 'error'
                else:
                    order_doc.state = 'done'
                    order_doc.text = 'empty order'
            already_processed_orders.append(order_doc._id)
            self.db.put(url=order_doc._id, data=encode_json(order_doc))

    def _create_tasks(self, providers=None, order_id=None):
        created = False
        for provider in providers:
            task_id = f"task-{provider}-{get_key(self.db.get('../_uuids'), 'uuids')[0]}"
            self.logger.info("create task %s" % task_id)
            doc = AttributeDict(
                _id=task_id,
                type="task",
                state="new",
                order_id=order_id,
                docs=providers[provider],
                provider=provider
            )
            self.db.put(url=doc._id, data=encode_json(doc))
            created = True
        return created

    def _update_order(self, tasks):
        for task in tasks:
            task_doc = AttributeDict(task['doc'])
            order_doc = get_doc(self.db.get(task_doc.order_id))
            if 'providers_done' not in order_doc:
                order_doc.providers_done = []
            providers = list(order_doc.providers.keys())
            providers_done = order_doc.providers_done
            providers_done.append(task_doc.provider)
            task_doc.state = 'done_checked'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            self.db.put(url=order_doc._id, data=encode_json(order_doc))
            self.logger.info(
                f'updating order for task {task_doc._id}, state: {order_doc.state}'
            )
            if sorted(providers) == sorted(providers_done):
                order_doc.state = 'done'
                update_docs_id = []
                [update_docs_id.extend(v) for v in order_doc.providers.values()]
                update_docs_id = list(set(update_docs_id))
                for doc_id in update_docs_id:
                    doc = get_doc(self.db.get(doc_id))
                    state = doc.state
                    next_state = 'undefined'
                    if state == 'new':
                        next_state = 'active'
                    if state == 'changed':
                        next_state = 'active'
                    if state == 'delete':
                        next_state = 'deleted'

                    # update state
                    self.db.update(
                        f'{self.db_name}/set-state', doc_id=doc_id, state=next_state
                    )
                    if next_state == 'active':
                        # save attachment of active doc
                        active_doc = get_doc(self.db.get(doc_id))
                        active_rev = active_doc._rev
                        self.db.put(
                            url=f'{active_doc._id}/{active_rev}',
                            data=json.dumps(active_doc)
                        )
                        self.db_design.put(
                            url=f'_update/set-active-rev/{doc_id}',
                            params=dict(active_rev=active_rev)
                        )
                self.db.put(url=order_doc._id, data=encode_json(order_doc))
                self.logger.info("order state: %s" % order_doc.state)

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_task, one=False,
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
        loop = asyncio.new_event_loop()
        tasks_open = loop.create_task(queue_tasks_open())
        orders_open = loop.create_task(queue_orders_open())
        tasks_done = loop.create_task(queue_tasks_done())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def run_once(self):
        queue_orders_open = self._create_queue(
            self._process_orders, run_once=True,
            **self.queue_kwargs['orders_open']
        )
        queue_orders_open()

        queue_tasks_open = self._create_queue(
            self._process_task, run_once=True,
            **self.queue_kwargs['tasks_open']
        )
        queue_tasks_open()

        queue_tasks_done = self._create_queue(
            self._update_order, run_once=True,
            **self.queue_kwargs['tasks_done']
        )
        queue_tasks_done()
