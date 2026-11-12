import asyncio
import time
import unittest
import urllib.parse
from unittest import mock

import httpx

from agenti.google import app as google_app
from agenti.google import session as session_module
from agenti.google.accounts import Accounts
from agenti.google.constants import SERVICES
from agenti.google.errors import explain
from agenti.google.session import Session

HEALTH_SCOPES = SERVICES["health"]["scopes"] + SERVICES["health_activity"]["scopes"]


def _query(url: str) -> dict:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))


class AuthUrlTest(unittest.TestCase):
    def setUp(self):
        self.flows = mock.Mock()
        patches = [mock.patch.object(google_app, "flows", self.flows),
                   mock.patch.object(google_app.OAuthApp, "credentials", staticmethod(lambda: ("cid", "sec")))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_main_grant_never_carries_health_scopes(self):
        q = _query(google_app.OAuthApp().auth_url("ana", ["calendar", "health", "health_activity"], ["tasks"]))
        scopes = q["scope"].split()
        self.assertFalse(any("googlehealth" in s for s in scopes))
        self.assertIn(SERVICES["tasks"]["scopes"][0], scopes)
        self.assertEqual(q["include_granted_scopes"], "false")
        self.assertEqual(self.flows.create.call_args.args[3], "main")

    def test_health_grant_has_only_health_scopes(self):
        q = _query(google_app.OAuthApp().auth_url("ana", ["health"], ["calendar", "health_activity"]))
        self.assertEqual(set(q["scope"].split()), set(HEALTH_SCOPES))
        self.assertEqual(self.flows.create.call_args.args[3], "health")


class CoveredTest(unittest.TestCase):
    def test_health_needs_its_own_grant(self):
        mixed = {"scopes": SERVICES["calendar"]["scopes"] + HEALTH_SCOPES}
        self.assertNotIn("health", Accounts.covered(mixed))
        self.assertIn("calendar", Accounts.covered(mixed))
        own = {**mixed, "health_scopes": HEALTH_SCOPES}
        self.assertTrue({"health", "health_activity"} <= set(Accounts.covered(own)))


class SessionTest(unittest.TestCase):
    def test_health_calls_use_the_health_token(self):
        info = {"refresh": "rm", "scopes": SERVICES["calendar"]["scopes"], "health_refresh": "rh", "health_scopes": HEALTH_SCOPES}
        s = Session("ana")
        s.tokens = {"main": ("tm", time.time() + 600), "health": ("th", time.time() + 600)}
        seen = []

        class Client:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def request(self, method, url, headers=None, **kw):
                seen.append((url, headers["Authorization"]))
                return httpx.Response(200, json={}, request=httpx.Request(method, url))

        with mock.patch.object(session_module.accounts, "get", return_value=info), \
             mock.patch.object(session_module.httpx, "AsyncClient", Client):
            asyncio.run(s._get("https://health.googleapis.com/v4/users/me/dataTypes/heart-rate/dataPoints"))
            asyncio.run(s._get("https://www.googleapis.com/calendar/v3/users/me/calendarList"))
            self.assertTrue(s.ready("health"))
        self.assertEqual([h for _, h in seen], ["Bearer th", "Bearer tm"])

    def test_health_not_ready_without_its_grant(self):
        info = {"refresh": "rm", "scopes": SERVICES["calendar"]["scopes"] + HEALTH_SCOPES}
        with mock.patch.object(session_module.accounts, "get", return_value=info):
            self.assertFalse(Session("ana").ready("health"))
            self.assertTrue(Session("ana").ready("calendar"))


class ErrorTest(unittest.TestCase):
    def _resp(self, body):
        return httpx.Response(403, json=body, request=httpx.Request("GET", "https://health.googleapis.com/x"))

    def test_mixed_scope_error_is_recognised(self):
        e = explain(self._resp({"error": {"status": "PERMISSION_DENIED",
                                          "message": "com.google.apps.framework.request.ForbiddenException: Could not mint UberMint from GaiaMint."}}))
        self.assertEqual(e.reason, "health_grant")

    def test_preview_and_missing_scope(self):
        preview = {"error": {"status": "PERMISSION_DENIED", "details": [{"reason": "API_PRIVATE_PREVIEW_ACCESS_DENIED"}]}}
        self.assertEqual(explain(self._resp(preview)).reason, "health_preview")
        scope = {"error": {"status": "PERMISSION_DENIED", "details": [{"reason": "MISSING_OAUTH_SCOPE"}]}}
        self.assertEqual(explain(self._resp(scope)).reason, "scope_missing")


if __name__ == "__main__":
    unittest.main()
