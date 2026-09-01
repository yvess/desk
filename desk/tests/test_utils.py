import unittest

import httpx

from desk.utils import (
    AttributeDict,
    CouchDBClient,
    CouchDBClientAsync,
    ObjectDict,
    calc_esr_checksum,
    decode_json,
    encode_json,
    get_doc,
    get_key,
    get_rows,
    parse_date,
)


class AttributeDictTestCase(unittest.TestCase):
    def test_item_and_attribute_access_are_the_same(self):
        ad = AttributeDict({"host": "www", "ip": "1.1.1.1"})
        self.assertEqual(ad["host"], "www")
        self.assertEqual(ad.host, "www")
        ad.ip = "1.1.1.2"
        self.assertEqual(ad["ip"], "1.1.1.2")

    def test_nested_mappings_become_attribute_dicts(self):
        ad = AttributeDict({"provides": {"domain": {"backend": "powerdns"}}})
        self.assertIsInstance(ad.provides, AttributeDict)
        self.assertEqual(ad.provides.domain.backend, "powerdns")

    def test_missing_key_raises_attribute_error(self):
        ad = AttributeDict({"host": "www"})
        with self.assertRaises(AttributeError):
            ad.nope
        with self.assertRaises(KeyError):
            ad["nope"]

    def test_mapping_protocol(self):
        ad = AttributeDict({"a": 1, "b": 2})
        self.assertEqual(len(ad), 2)
        self.assertEqual(sorted(ad), ["a", "b"])
        del ad["a"]
        self.assertEqual(list(ad), ["b"])


class ObjectDictTestCase(unittest.TestCase):
    def test_keywords_become_attributes(self):
        od = ObjectDict(couchdb_db="desk_drawer", worker_is_foreman=True)
        self.assertEqual(od.couchdb_db, "desk_drawer")
        self.assertTrue(od.worker_is_foreman)


class DateTestCase(unittest.TestCase):
    def test_parse_date(self):
        self.assertEqual(parse_date("2026-09-17").isoformat(), "2026-09-17")

    def test_parse_date_force_day_start(self):
        self.assertEqual(
            parse_date("2026-09-17", force_day="start").isoformat(), "2026-09-01"
        )

    def test_parse_date_force_day_end(self):
        self.assertEqual(
            parse_date("2026-09-17", force_day="end").isoformat(), "2026-09-30"
        )
        self.assertEqual(  # leap year
            parse_date("2024-02-05", force_day="end").isoformat(), "2024-02-29"
        )

    def test_parse_date_unknown_force_day_raises(self):
        with self.assertRaises(ValueError):
            parse_date("2026-09-17", force_day="middle")


class EsrChecksumTestCase(unittest.TestCase):
    def test_known_reference(self):
        self.assertEqual(calc_esr_checksum("313947143000901"), 8)

    def test_leading_zeros_are_ignored(self):
        self.assertEqual(calc_esr_checksum("000313947143000901"), 8)


class JsonTestCase(unittest.TestCase):
    def test_decode_json_accepts_str_and_bytes(self):
        self.assertEqual(decode_json('{"a": 1}'), {"a": 1})
        self.assertEqual(decode_json(b'{"a": 1}'), {"a": 1})

    def test_decode_json_child(self):
        self.assertEqual(decode_json('{"rows": [1, 2]}', child="rows"), [1, 2])

    def test_encode_json_serializes_object_dicts(self):
        encoded = encode_json({"settings": ObjectDict(couchdb_db="desk_drawer")})
        self.assertEqual(encoded, '{"settings": {"couchdb_db": "desk_drawer"}}')


def _response(payload):
    return httpx.Response(
        200, json=payload, request=httpx.Request("GET", "http://cdb")
    )


class ResponseHelpersTestCase(unittest.TestCase):
    def test_get_rows(self):
        response = _response({"rows": [{"id": "dns-test"}]})
        self.assertEqual(get_rows(response), [{"id": "dns-test"}])

    def test_get_rows_returns_none_for_non_json_body(self):
        response = httpx.Response(
            200, text="not json", request=httpx.Request("GET", "http://cdb")
        )
        self.assertIsNone(get_rows(response))

    def test_get_rows_returns_none_for_error_body(self):
        # CouchDB answers errors with a JSON object without "rows"
        response = _response({"error": "not_found", "reason": "missing_named_view"})
        self.assertIsNone(get_rows(response))

    def test_get_rows_returns_none_for_array_body(self):
        # _list handlers may answer with a JSON array
        response = _response([{"id": "dns-test"}])
        self.assertIsNone(get_rows(response))

    def test_get_doc_unwraps_view_row(self):
        doc = get_doc(_response({"doc": {"_id": "dns-test", "type": "domain"}}))
        self.assertIsInstance(doc, AttributeDict)
        self.assertEqual(doc._id, "dns-test")

    def test_get_doc_on_plain_document(self):
        doc = get_doc(_response({"_id": "dns-test"}))
        self.assertEqual(doc._id, "dns-test")

    def test_get_key(self):
        self.assertEqual(get_key(_response({"_rev": "2-abc"}), "_rev"), "2-abc")


def _handler(request):
    return httpx.Response(200, json={"_id": "dns-test"}, headers={"ETag": '"2-abc"'})


def _client(handler=_handler, client_class=CouchDBClient):
    return client_class(
        base_url="http://cdb:5984/desk_drawer",
        transport=httpx.MockTransport(handler),
    )


class CouchDBClientTestCase(unittest.TestCase):
    """The clients attach CouchDB's ETag as `response.rev`."""

    def test_request_sets_rev_from_etag(self):
        with _client() as client:
            self.assertEqual(client.get("/dns-test").rev, "2-abc")

    def test_rev_helper(self):
        with _client() as client:
            self.assertEqual(client.rev("/dns-test"), "2-abc")

    def test_rev_is_none_without_etag(self):
        with _client(lambda request: httpx.Response(200, json={})) as client:
            self.assertIsNone(client.get("/dns-test").rev)

    def test_rev_is_none_on_failed_write(self):
        # error responses carry no ETag, callers get rev=None
        handler = lambda request: httpx.Response(409, json={"error": "conflict"})
        with _client(handler) as client:
            self.assertIsNone(client.put("/dns-test", content="{}").rev)

    def test_weak_etag_is_unwrapped(self):
        # a proxy in front of CouchDB (e.g. nginx gzip) may weaken the ETag
        handler = lambda request: httpx.Response(200, headers={"ETag": 'W/"2-abc"'})
        with _client(handler) as client:
            self.assertEqual(client.get("/dns-test").rev, "2-abc")

    def test_streamed_response_has_rev(self):
        # the _changes feed uses stream(), which bypasses request()
        with _client() as client:
            with client.stream("GET", "/_changes") as response:
                self.assertEqual(response.rev, "2-abc")

    def test_db_factory(self):
        client = CouchDBClient.db(
            "http://admin:admin@cdb:5984", db_name="desk_drawer",
            transport=httpx.MockTransport(_handler),
        )
        with client:
            self.assertEqual(str(client.base_url), "http://cdb:5984/desk_drawer/")
            self.assertEqual(client.get("/dns-test").rev, "2-abc")

    def test_db_factory_without_credentials(self):
        client = CouchDBClient.db(
            "http://localhost:5984", db_name="desk_drawer",
            transport=httpx.MockTransport(_handler),
        )
        with client:
            self.assertEqual(
                str(client.base_url), "http://localhost:5984/desk_drawer/"
            )
            self.assertEqual(client.get("/dns-test").rev, "2-abc")


class CouchDBClientAsyncTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_request_sets_rev_from_etag(self):
        """Regression: request() used to delegate to a non-existent super()._request()."""
        async with _client(client_class=CouchDBClientAsync) as client:
            self.assertEqual((await client.get("/dns-test")).rev, "2-abc")
            self.assertEqual(await client.rev("/dns-test"), "2-abc")

    async def test_streamed_response_has_rev(self):
        async with _client(client_class=CouchDBClientAsync) as client:
            async with client.stream("GET", "/_changes") as response:
                self.assertEqual(response.rev, "2-abc")


if __name__ == "__main__":
    unittest.main()
