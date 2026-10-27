import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import Request
from fastapi.responses import Response

import auth
from access import require_display
from features.ear import broadcast
from features.ear.broadcast import broadcast_event, register, unregister
from system_api import _display_response

WEB = Path(__file__).resolve().parents[1] / "web" / "display"


class FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sent: list[dict] = []
        self.ws = SimpleNamespace(send=self._send)
        self.page = {"visible": "visible"}

    async def _send(self, data: str) -> None:
        self.sent.append(json.loads(data))


class RemoteDisplayBroadcastTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        broadcast.SESSIONS.clear()

    async def asyncTearDown(self) -> None:
        broadcast.SESSIONS.clear()

    async def test_broadcast_event_reaches_all_active_sessions(self) -> None:
        s1, s2 = FakeSession("kiosk"), FakeSession("remote_tablet")
        register(s1)
        register(s2)
        await broadcast_event(s1, type="partial", utt="u1", text="accendi la", stable=1)
        self.assertEqual(len(s1.sent), 1)
        self.assertEqual(len(s2.sent), 1)
        self.assertEqual(s1.sent[0]["text"], "accendi la")
        self.assertEqual(s2.sent[0]["text"], "accendi la")

    async def test_transcript_origin_flag_distinguishes_source_from_mirrors(self) -> None:
        kiosk, remote = FakeSession("kiosk"), FakeSession("remote_browser")
        register(kiosk)
        register(remote)
        await broadcast_event(kiosk, type="transcript", text="spegni le luci", utt="u2", speaker="anna")
        self.assertNotIn("origin", kiosk.sent[0])
        self.assertFalse(remote.sent[0]["origin"])
        self.assertEqual(remote.sent[0]["text"], "spegni le luci")
        self.assertEqual(remote.sent[0]["speaker"], "anna")

    async def test_session_lifecycle_registration(self) -> None:
        s = FakeSession("test")
        register(s)
        self.assertIn(s, broadcast.all_sessions())
        unregister(s)
        self.assertNotIn(s, broadcast.all_sessions())


class DisplaySessionCookieTest(unittest.TestCase):
    def test_display_response_sets_signed_cookie_when_missing(self) -> None:
        req = SimpleNamespace(cookies={}, url=SimpleNamespace(scheme="http"))
        res = Response("ok")
        out = _display_response(req, res)
        cookies = [h[1].decode("latin-1") for h in out.raw_headers if h[0].lower() == b"set-cookie"]
        self.assertTrue(any(auth.SESSION_COOKIE in c and auth.verify(c.split(";")[0].split("=", 1)[1].strip('"')) == "display" for c in cookies))

    def test_display_response_preserves_existing_valid_session(self) -> None:
        admin_token = auth.issue("admin")
        req = SimpleNamespace(cookies={auth.SESSION_COOKIE: admin_token}, url=SimpleNamespace(scheme="http"))
        res = Response("ok")
        out = _display_response(req, res)
        cookies = [h[1].decode("latin-1") for h in out.raw_headers if h[0].lower() == b"set-cookie"]
        self.assertEqual(len(cookies), 0)


class RequireDisplaySecurityTest(unittest.TestCase):
    def fake_request(self, host: str, method: str = "GET", cookie: str = "") -> Request:
        scope = {
            "type": "http",
            "method": method,
            "client": (host, 12345),
            "headers": [(b"cookie", f"{auth.SESSION_COOKIE}={cookie}".encode())] if cookie else [],
        }
        return Request(scope)

    def test_private_ip_allowed_for_read_only_get(self) -> None:
        require_display(self.fake_request("192.168.1.50", "GET"))
        require_display(self.fake_request("10.0.0.5", "HEAD"))

    def test_public_ip_without_session_denied_for_get(self) -> None:
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            require_display(self.fake_request("8.8.8.8", "GET"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_private_ip_denied_for_post_without_session(self) -> None:
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            require_display(self.fake_request("192.168.1.50", "POST"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_valid_display_session_cookie_allowed_for_all_methods(self) -> None:
        token = auth.issue("display")
        require_display(self.fake_request("192.168.1.50", "GET", token))
        require_display(self.fake_request("192.168.1.50", "POST", token))


class EarJsScriptVerificationTest(unittest.TestCase):
    def test_ear_js_connects_before_mic_check(self) -> None:
        src = (WEB / "ear.js").read_text(encoding="utf-8")
        conn_idx = src.index("connect();\n    if (!micAllowed())")
        self.assertGreater(conn_idx, 0)

    def test_transcript_guard_checks_origin_and_mic_live_before_ask(self) -> None:
        src = (WEB / "ear.js").read_text(encoding="utf-8")
        self.assertIn("if (ev.origin !== false && micLive())", src)
        self.assertIn("if (D.Captions) D.Captions.event(ev);", src)


if __name__ == "__main__":
    unittest.main()
