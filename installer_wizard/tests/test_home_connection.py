import unittest
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.home_assistant import address, connection_api, probe
from features.home_assistant.connection import AuthError, HAError, HomeConnection


class AddressTest(unittest.TestCase):
    def test_bare_hosts_get_scheme_and_default_port(self):
        self.assertEqual(address.normalize("192.168.1.20"), "http://192.168.1.20:8123")
        self.assertEqual(address.normalize("homeassistant.local"), "http://homeassistant.local:8123")
        self.assertEqual(address.normalize("192.168.1.20:8124"), "http://192.168.1.20:8124")

    def test_explicit_urls_are_kept_and_trailing_slash_dropped(self):
        self.assertEqual(address.normalize("https://casa.example.org/"), "https://casa.example.org")
        self.assertEqual(address.normalize("http://10.0.0.5:8123/ha/"), "http://10.0.0.5:8123/ha")
        self.assertEqual(address.normalize("http://[fd00::5]:8123"), "http://[fd00::5]:8123")

    def test_dangerous_or_malformed_addresses_are_refused(self):
        for bad in ("", "ftp://host", "http://user:pw@host", "http://host?x=1", "http://169.254.169.254",
                    "http://bad host", "http://host:99999", "javascript:alert(1)", "x" * 300):
            with self.assertRaises(ValueError, msg=bad):
                address.normalize(bad)

    def test_parse_splits_dedups_and_limits(self):
        self.assertEqual(address.parse("10.0.0.1, 10.0.0.1\nhttps://a.example.org"), ["http://10.0.0.1:8123", "https://a.example.org"])
        with self.assertRaises(ValueError):
            address.parse([f"10.0.0.{i}" for i in range(1, 9)])

    def test_candidates_skip_broken_entries(self):
        self.assertEqual(address.candidates("http://10.0.0.1:8123", "ftp://x, 10.0.0.2"), ["http://10.0.0.1:8123", "http://10.0.0.2:8123"])
        self.assertEqual(address.candidates("", ""), [])


def client_for(handler):
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    return mock.patch.object(probe.httpx, "AsyncClient", lambda **kw: real(transport=transport, **{k: v for k, v in kw.items() if k != "verify"}))


class ProbeTest(unittest.IsolatedAsyncioTestCase):
    async def test_success_reports_version_and_name(self):
        with client_for(lambda r: httpx.Response(200, json={"version": "2026.9.1", "location_name": "Casa"})):
            result = await probe.probe("http://10.0.0.1:8123", "tok", True)
        self.assertEqual((result["ok"], result["version"], result["name"]), (True, "2026.9.1", "Casa"))

    async def test_wrong_token_and_missing_token(self):
        with client_for(lambda r: httpx.Response(401)):
            self.assertEqual((await probe.probe("http://h:8123", "tok", True))["state"], "auth")
            self.assertEqual((await probe.probe("http://h:8123", "", True))["state"], "no_token")

    async def test_not_home_assistant_and_redirect(self):
        with client_for(lambda r: httpx.Response(200, text="<html>")):
            self.assertEqual((await probe.probe("http://h:8123", "t", True))["state"], "not_home_assistant")
        with client_for(lambda r: httpx.Response(302, headers={"location": "https://x"})):
            self.assertEqual((await probe.probe("http://h:8123", "t", True))["state"], "redirect")

    async def test_unreachable_and_timeout_are_explained(self):
        def refuse(request):
            raise httpx.ConnectError("refused")

        def slow(request):
            raise httpx.ConnectTimeout("slow")

        with client_for(refuse):
            self.assertEqual((await probe.probe("http://h:8123", "t", True))["state"], "unreachable")
        with client_for(slow):
            self.assertEqual((await probe.probe("http://h:8123", "t", True))["state"], "timeout")

    async def test_token_is_sent_as_bearer_only(self):
        seen = {}

        def capture(request):
            seen["auth"] = request.headers.get("authorization")
            seen["url"] = str(request.url)
            return httpx.Response(200, json={})

        with client_for(capture):
            await probe.probe("http://h:8123", "secret", True)
        self.assertEqual(seen, {"auth": "Bearer secret", "url": "http://h:8123/api/config"})


class OrderTest(unittest.IsolatedAsyncioTestCase):
    def make(self, outcomes):
        link = HomeConnection.__new__(HomeConnection)
        link.url, link._joined, calls = "", False, []

        async def session(s):
            calls.append(s["url"])
            outcome = outcomes[s["url"]]
            if outcome == "join":
                link._joined = True
                link.url = s["url"]
                return
            if outcome == "join-then-drop":
                link._joined = True
                raise ConnectionError("caduta")
            raise outcome

        link._session = session
        return link, calls

    async def test_next_address_is_tried_until_one_answers(self):
        link, calls = self.make({"a": OSError("giu"), "b": "join"})
        await link._try_addresses({"urls": ["a", "b"]})
        self.assertEqual(calls, ["a", "b"])

    async def test_last_working_address_goes_first(self):
        link, calls = self.make({"a": "join", "b": "join"})
        link.url = "b"
        await link._try_addresses({"urls": ["a", "b"]})
        self.assertEqual(calls, ["b"])

    async def test_wrong_token_stops_immediately(self):
        link, calls = self.make({"a": AuthError("no"), "b": "join"})
        with self.assertRaises(AuthError):
            await link._try_addresses({"urls": ["a", "b"]})
        self.assertEqual(calls, ["a"])

    async def test_drop_after_joining_does_not_hop(self):
        link, calls = self.make({"a": "join-then-drop", "b": "join"})
        with self.assertRaises(ConnectionError):
            await link._try_addresses({"urls": ["a", "b"]})
        self.assertEqual(calls, ["a"])

    async def test_all_failing_reports_every_address(self):
        link, _ = self.make({"a": OSError("x"), "b": OSError("y")})
        with self.assertRaises(HAError) as raised:
            await link._try_addresses({"urls": ["a", "b"]})
        self.assertIn("a: OSError", str(raised.exception))
        self.assertIn("b: OSError", str(raised.exception))


class ConnectionApiTest(unittest.TestCase):
    def setUp(self):
        self.env = {}
        brain = mock.Mock(status="online", error="", url="http://10.0.0.1:8123", ha_version="2026.9", ha_name="Casa", online=True)
        brain.settings.side_effect = lambda: {"urls": ["http://10.0.0.1:8123"], "token": self.env.get("HOME_ASSISTANT_TOKEN", "old"),
                                              "verify_ssl": True, "enabled": True}
        patches = (mock.patch.object(connection_api.home, "brain", brain),
                   mock.patch.object(connection_api, "write_env", side_effect=self.env.update),
                   mock.patch.object(connection_api, "read_env", return_value={}),
                   mock.patch.object(connection_api, "discovered", return_value=["http://10.0.0.9:8123"]),
                   mock.patch.object(connection_api.registry, "note_env_change"),
                   mock.patch.object(connection_api.store, "event"))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        app = FastAPI()
        app.include_router(connection_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def test_get_never_returns_the_token(self):
        data = self.client.get("/api/home/connection").json()
        self.assertTrue(data["token_set"])
        self.assertNotIn("old", str(data))
        self.assertEqual(data["suggestions"], ["http://10.0.0.9:8123"])

    def test_put_saves_addresses_in_order_and_keeps_token_when_blank(self):
        response = self.client.put("/api/home/connection", json={"urls": ["10.0.0.1", "https://casa.example.org"], "token": "", "verify_ssl": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.env["HOME_ASSISTANT_URL"], "http://10.0.0.1:8123")
        self.assertEqual(self.env["HOME_ASSISTANT_URLS"], "https://casa.example.org")
        self.assertEqual(self.env["HOME_ASSISTANT_VERIFY_SSL"], "0")
        self.assertNotIn("HOME_ASSISTANT_TOKEN", self.env)

    def test_put_sets_and_clears_token(self):
        self.client.put("/api/home/connection", json={"urls": ["10.0.0.1"], "token": "abc.def"})
        self.assertEqual(self.env["HOME_ASSISTANT_TOKEN"], "abc.def")
        self.client.put("/api/home/connection", json={"urls": ["10.0.0.1"], "clear_token": True})
        self.assertEqual(self.env["HOME_ASSISTANT_TOKEN"], "")

    def test_invalid_input_is_rejected(self):
        self.assertEqual(self.client.put("/api/home/connection", json={"urls": ["ftp://x"]}).status_code, 400)
        self.assertEqual(self.client.put("/api/home/connection", json={"urls": ["10.0.0.1"], "token": "a b"}).status_code, 400)
        self.assertEqual(self.client.post("/api/home/connection/test", json={"urls": ["http://169.254.169.254"]}).status_code, 400)

    def test_test_uses_stored_values_and_returns_results(self):
        async def fake(urls, token, verify):
            return [{"url": u, "ok": True, "token": token} for u in urls]

        with mock.patch.object(connection_api.probe, "probe_all", side_effect=fake):
            results = self.client.post("/api/home/connection/test", json={}).json()["results"]
            typed = self.client.post("/api/home/connection/test", json={"urls": ["10.0.0.7"], "token": "new"}).json()["results"]
        self.assertEqual(results[0]["token"], "old")
        self.assertEqual((typed[0]["url"], typed[0]["token"]), ("http://10.0.0.7:8123", "new"))


if __name__ == "__main__":
    unittest.main()
