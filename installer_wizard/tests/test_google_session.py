import asyncio
import unittest
from unittest import mock

import httpx

from features.google import session as session_module
from features.google.errors import GoogleApiError, explain


def response(status: int, body: dict | None = None, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=body if body is not None else {}, headers=headers or {}, request=httpx.Request("GET", "https://x.googleapis.com/a"))


class ExplainTest(unittest.TestCase):
    def test_disabled_api_gives_name_and_safe_link(self):
        body = {"error": {"code": 403, "message": "Google Health API has not been used in project 1 before or it is disabled.", "status": "PERMISSION_DENIED",
                          "details": [{"reason": "SERVICE_DISABLED", "metadata": {"service": "health.googleapis.com",
                                       "activationUrl": "https://console.developers.google.com/apis/api/health.googleapis.com/overview?project=1"}}]}}
        err = explain(response(403, body))
        self.assertEqual(err.reason, "api_disabled")
        self.assertIn("Google Health API", str(err))
        self.assertTrue(err.activation.startswith("https://console.developers.google.com/"))

    def test_unsafe_activation_link_is_dropped(self):
        body = {"error": {"details": [{"reason": "SERVICE_DISABLED", "metadata": {"activationUrl": "https://evil.example/x"}}]}}
        self.assertEqual(explain(response(403, body)).activation, "")

    def test_other_reasons(self):
        self.assertEqual(explain(response(403, {"error": {"details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}})).reason, "scope_missing")
        self.assertEqual(explain(response(400, {"error": {"status": "FAILED_PRECONDITION", "message": "ACCOUNT_NOT_LINKED"}})).reason, "health_profile_missing")
        self.assertEqual(explain(response(429)).reason, "quota")
        self.assertEqual(explain(response(404)).reason, "not_found")
        self.assertIsInstance(explain(response(500)), ValueError)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.store = {"anna": {"refresh": "r", "scopes": []}}
        patch = mock.patch.object(session_module, "accounts")
        self.accounts = patch.start()
        self.addCleanup(patch.stop)
        self.accounts.get.side_effect = lambda slug: dict(self.store.get(slug, {}))
        self.accounts.put.side_effect = lambda slug, entry: self.store[slug].update(entry)
        self.accounts.granted.return_value = ["calendar"]
        self.tokens = mock.AsyncMock(return_value={"access_token": "t", "expires_in": 3600})
        patch = mock.patch.object(session_module.oauth, "token", self.tokens)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch.object(session_module.asyncio, "sleep", mock.AsyncMock())
        patch.start()
        self.addCleanup(patch.stop)

    def run_call(self, replies):
        calls = iter(replies)

        async def request(self_client, method, url, **kw):
            return next(calls)
        with mock.patch.object(httpx.AsyncClient, "request", request):
            return asyncio.run(session_module.Session("anna")._get("https://x.googleapis.com/a"))

    def test_expired_token_is_renewed_once(self):
        self.assertEqual(self.run_call([response(401), response(200, {"ok": 1})]), {"ok": 1})
        self.assertEqual(self.tokens.await_count, 2)

    def test_rate_limit_and_server_errors_are_retried(self):
        self.assertEqual(self.run_call([response(429, headers={"retry-after": "1"}), response(503), response(200, {"ok": 2})]), {"ok": 2})

    def test_errors_become_google_api_errors(self):
        with self.assertRaises(GoogleApiError):
            self.run_call([response(403, {"error": {"details": [{"reason": "SERVICE_DISABLED"}]}})])

    def test_revoked_refresh_token_marks_account(self):
        self.tokens.side_effect = ValueError("Google: autorizzazione scaduta o revocata: ricollega l'account")
        with self.assertRaises(ValueError):
            self.run_call([])
        self.assertTrue(self.store["anna"]["revoked"])
        self.assertFalse(session_module.Session("anna").ready("calendar"))

    def test_concurrent_calls_share_one_refresh(self):
        async def many():
            s = session_module.Session("anna")
            return await asyncio.gather(*(s._access() for _ in range(5)))
        self.assertEqual(asyncio.run(many()), ["t"] * 5)
        self.assertEqual(self.tokens.await_count, 1)


class ScopeTest(SessionTest):
    def test_refresh_listing_fewer_scopes_does_not_turn_services_off(self):
        self.store["anna"]["scopes"] = ["a", "tasks"]
        self.tokens.return_value = {"access_token": "t", "expires_in": 3600, "scope": "a"}
        asyncio.run(session_module.Session("anna")._access())
        self.assertEqual(self.store["anna"]["scopes"], ["a", "tasks"])

    def test_refresh_adds_new_scopes(self):
        self.store["anna"]["scopes"] = ["a"]
        self.tokens.return_value = {"access_token": "t", "expires_in": 3600, "scope": "a b"}
        asyncio.run(session_module.Session("anna")._access())
        self.assertEqual(self.store["anna"]["scopes"], ["a", "b"])

    def test_insufficient_scope_rechecks_with_google(self):
        self.store["anna"]["scopes"] = ["a", "tasks"]
        info = response(200, {"scope": "a"})
        calls = iter([response(403, {"error": {"details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}})])

        async def request(self_client, method, url, **kw):
            return next(calls)

        async def get(self_client, url, **kw):
            return info
        with mock.patch.object(httpx.AsyncClient, "request", request), mock.patch.object(httpx.AsyncClient, "get", get):
            with self.assertRaises(GoogleApiError):
                asyncio.run(session_module.Session("anna")._get("https://tasks.googleapis.com/x"))
        self.assertEqual(self.store["anna"]["scopes"], ["a"])
