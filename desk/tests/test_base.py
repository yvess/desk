import json
import unittest

import httpx

from desk.plugin.base import VersionDoc
from desk.utils import AttributeDict, CouchDBClient


class VersionDocTestCase(unittest.TestCase):
    """Regression: create_version used raw responses as docs and `.rev`
    instead of `_rev`."""

    def test_create_version(self):
        server_doc = {
            "_id": "dns-test", "_rev": "1-old", "type": "domain", "state": "active"
        }
        requests = []

        def handler(request):
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200, json=server_doc,
                    headers={"ETag": f'"{server_doc["_rev"]}"'}
                )
            if request.method == "PUT" and request.url.path.endswith("/1-old"):
                server_doc["_rev"] = "2-att"  # attachment write bumps the rev
                return httpx.Response(
                    201, json={"ok": True}, headers={"ETag": '"2-att"'}
                )
            return httpx.Response(
                201, json={"ok": True}, headers={"ETag": '"3-new"'}
            )

        with CouchDBClient(
            base_url="http://cdb:5984/desk_drawer",
            transport=httpx.MockTransport(handler),
        ) as db:
            doc = AttributeDict(
                {"_id": "dns-test", "_rev": "1-old", "type": "domain", "state": "new"}
            )
            version_doc = VersionDoc(db, doc)
            version_doc.create_version()

        self.assertEqual(
            [(r.method, r.url.path) for r in requests],
            [
                ("GET", "/desk_drawer/dns-test"),
                ("PUT", "/desk_drawer/dns-test/1-old"),
                ("GET", "/desk_drawer/dns-test"),
                ("PUT", "/desk_drawer/dns-test"),
            ],
        )
        self.assertEqual(requests[1].url.params["rev"], "1-old")
        old_version = json.loads(requests[1].content)
        self.assertEqual(old_version["_rev"], "1-old")
        final_doc = json.loads(requests[3].content)
        self.assertEqual(final_doc["state"], "changed")
        self.assertEqual(final_doc["prev_rev"], "1-old")
        self.assertEqual(final_doc["_rev"], "2-att")


if __name__ == "__main__":
    unittest.main()
