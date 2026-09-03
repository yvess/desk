"""Regression tests for the daemon side: Worker queues and the Updater.

Both talk to CouchDB through a real `CouchDBClient`; only the HTTP transport
is stubbed. The DNS backend handed to the Updater is a plain recorder, the
same shape `desk/plugin/dns` backends have.
"""
import unittest

import httpx

from desk import Worker
from desk.plugin.base import Updater
from desk.plugin.dns.powerdns import Powerdns
from desk.utils import AttributeDict, CouchDBClient, ObjectDict


def client(handler):
    return CouchDBClient.db(
        'http://cdb:5984', db_name='desk_drawer',
        transport=httpx.MockTransport(handler),
    )


class WorkerQueueTestCase(unittest.TestCase):
    """The startup read of a task queue view."""

    def queue_once(self, status, body):
        def handler(request):
            self.requests.append(request)
            return httpx.Response(status, json=body)

        self.requests = []
        self.processed = []
        worker = object.__new__(Worker)
        worker.db = client(handler)
        self.addCleanup(worker.db.close)
        return worker._create_queue(
            self.processed.append, run_once=True, queue_name='tasks_open'
        )

    def test_open_tasks_are_handed_to_the_item_function(self):
        rows = [{'id': 'task-1', 'doc': {'_id': 'task-1', 'provider': 'dns'}}]
        self.queue_once(200, {'rows': rows})()
        self.assertEqual(self.processed, [rows])
        self.assertEqual(
            self.requests[0].url.path,
            '/desk_drawer/_design/desk_drawer/_view/tasks_open',
        )
        self.assertEqual(self.requests[0].url.params['include_docs'], 'true')

    def test_a_missing_view_is_an_error_not_an_empty_queue(self):
        """get_rows() turned the error body into None, so an outdated design
        doc left the worker idling as if there were no open tasks."""
        queue = self.queue_once(
            404, {'error': 'not_found', 'reason': 'missing_named_view'}
        )
        with self.assertRaises(httpx.HTTPStatusError):
            queue()
        self.assertEqual(self.processed, [])


class RecorderService:
    """What the Updater needs from a DNS backend, recording what it gets."""

    map_doc_id = 'map-ips'

    def __init__(self):
        self.lookup_map = None
        self.docs = None

    def set_docs(self, doc, active_doc=None):
        self.docs = (doc, active_doc)

    def set_lookup_map(self, doc):
        self.lookup_map = doc['map']

    def create(self):
        return True

    update = delete = create


class UpdaterLookupMapTestCase(unittest.TestCase):
    """The map doc is optional, but a failing CouchDB is not."""

    def updater(self, map_response):
        def handler(request):
            return map_response

        self.service = RecorderService()
        doc = AttributeDict({
            '_id': 'domain-test-ch', 'type': 'domain', 'state': 'new',
            'domain': 'test.ch',
        })
        with client(handler) as db:
            return Updater(db, doc, self.service)

    def test_the_map_doc_is_handed_to_the_service(self):
        self.updater(httpx.Response(
            200, json={'_id': 'map-ips', 'map': {'$ip_web': '1.2.3.4'}}
        ))
        self.assertEqual(self.service.lookup_map, {'$ip_web': '1.2.3.4'})

    def test_a_missing_map_doc_is_tolerated(self):
        self.updater(httpx.Response(
            404, json={'error': 'not_found', 'reason': 'missing'}
        ))
        self.assertIsNone(self.service.lookup_map)
        self.assertIsNotNone(self.service.docs)

    def test_any_other_error_stops_the_task(self):
        """A 500 or 401 used to be skipped silently; the task then died later
        with AttributeError on the unset lookup_map."""
        with self.assertRaises(httpx.HTTPStatusError):
            self.updater(httpx.Response(500, json={'error': 'internal'}))


class DnsBaseLookupMapTestCase(unittest.TestCase):
    def test_a_backend_starts_with_an_empty_lookup_map(self):
        # a $ip_ value then fails with KeyError naming it, not AttributeError
        settings = ObjectDict(powerdns_backend='sqlite', powerdns_db=':memory:')
        with Powerdns(settings) as pdns:
            self.assertEqual(pdns.lookup_map, {})
            with self.assertRaises(KeyError):
                pdns.lookup_map['$ip_web']


if __name__ == '__main__':
    unittest.main()
