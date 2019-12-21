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
        self.db_design = CouchDBSession.db_design(settings.couchdb_uri, db_name=settings.couchdb_db)
        self.db_async = lambda: CouchDBSessionAsync.db(settings.couchdb_uri, db_name=settings.couchdb_db)
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

    def _process_tasks(self, tasks):
        for seq in tasks:
            self.logger.info('ready for processing tasks')
            provider_lookup = {}
            task_doc = AttributeDict(seq['doc'])
            for (service_type, services) in self.provides.items():
                for service in services:
                    provider_lookup[service['name']] = service_type

                if task_doc.provider in provider_lookup:
                    self._run_tasks(task_id=task_doc._id, docs=task_doc.docs)

    def _run_tasks(self, task_id, docs):
        successfull_tasks = []
        for doc_id in docs:
            doc = get_doc(self.db.get(doc_id))
            self.logger.info('do task %s' % task_id)
            was_successfull = self._do_task(doc)
            successfull_tasks.append(was_successfull)
        task_doc = get_doc(self.db.get(task_id))
        if all(successfull_tasks):
            task_doc.state = 'done'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            self.logger.info(f'task done doc_id: {task_doc._id}')
        else:
            task_doc.state = 'error'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            self.logger.info(f'task error doc_id: {task_doc._id}')

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

    def _create_queue(self, item_function, run_once=False, queue_name=''):
        # print('_create_queue', queue_name)
        if run_once is True:
            def queue_once():
                items = get_rows(self.db_design.get(f'_view/{queue_name}', params={'include_docs': 'true'}))
                if items:
                    item_function(items)
            return queue_once
        else:
            async def queue():
                items = get_rows(self.db_design.get(f'_view/{queue_name}', params={'include_docs': 'true'}))
                if items:
                    item_function(items)

                params = dict(
                    feed='continuous', heartbeat='true', # continuous, eventsource
                    since='now', timeout=60
                )
                params.update(**self.queue_kwargs[queue_name])
                async with self.db_async().get('_changes', params=params) as response: # _changes
                    async for line in response.content:
                        line_str = line.decode('utf8').strip()
                        if line_str:
                            data = decode_json(line_str)
                            item_function([data])
            return queue

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=False, queue_name='tasks_open'
        )

        loop = asyncio.get_event_loop()
        loop.create_task(queue_tasks_open())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def run_once(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=True, queue_name='tasks_open'
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
        for seq in orders:
            providers, docs = {}, []
            already_processed_orders = []
            items = get_rows(self.db_design.get('_view/new_by_editor', params=dict(include_docs='true')))
            order_doc = AttributeDict(seq['doc'])
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

    def _update_order(self, tasks):  # tasks_done changes filter
        for task in tasks:
            task_doc = AttributeDict(task['doc'])
            order_doc = get_doc(self.db.get(task_doc.order_id))
            if 'error' in order_doc and order_doc.error == 'not_found' and order_doc.reason == 'deleted':
                task_doc.state = 'done_checked' # order deleted, disable task
                self.db.put(url=task_doc._id, data=encode_json(task_doc))
                continue
            if 'providers_done' not in order_doc:
                order_doc.providers_done = []
            providers = list(order_doc.providers.keys())
            providers_done = order_doc.providers_done
            providers_done.append(task_doc.provider)
            task_doc.state = 'done_checked'
            self.db.put(url=task_doc._id, data=encode_json(task_doc))
            order_doc._rev = self.db.put(url=order_doc._id, data=encode_json(order_doc)).rev
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
                    self.db_design.put(
                        url=f'_update/set-state/{doc_id}', params=dict(state=next_state)
                    )
                    if next_state == 'active':
                        # save attachment of active doc
                        active_doc = get_doc(self.db.get(doc_id))
                        active_rev = active_doc._rev
                        self.db.put(
                            url=f'{active_doc._id}/{active_rev}',
                            data=encode_json(active_doc)
                        )
                        self.db_design.put(
                            url=f'_update/set-active-rev/{doc_id}',
                            params=dict(active_rev=active_rev)
                        )
                self.db.put(url=order_doc._id, data=encode_json(order_doc))
                self.logger.info('order state: %s' % order_doc.state)

    def run(self):
        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=False, queue_name='tasks_open'
        )
        queue_orders_open = self._create_queue(
            self._process_orders, run_once=False, queue_name='orders_open'
        )
        queue_tasks_done = self._create_queue(
            self._update_order, run_once=False, queue_name='tasks_done'
        )

        loop = asyncio.get_event_loop()
        loop.create_task(queue_tasks_open())
        loop.create_task(queue_orders_open())
        loop.create_task(queue_tasks_done())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def run_once(self):
        queue_orders_open = self._create_queue(
            self._process_orders, run_once=True, queue_name='orders_open'
        )
        queue_orders_open()

        queue_tasks_open = self._create_queue(
            self._process_tasks, run_once=True, queue_name='tasks_open'
        )
        queue_tasks_open()

        queue_tasks_done = self._create_queue(
            self._update_order, run_once=True, queue_name='tasks_done'
        )
        queue_tasks_done()
