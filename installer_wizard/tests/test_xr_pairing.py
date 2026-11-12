import asyncio
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from agenti.desktop import xr_api, xr_pairing
from agenti.desktop.xr_pairing import XrPairing


class Clock:

    def __init__(self, t: float = 1_800_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class Request:

    def __init__(self, body=None, cookies=None, scheme="https") -> None:
        self.raw = json.dumps(body or {}).encode()
        self.cookies = cookies or {}
        self.url = mock.Mock(scheme=scheme)

    async def body(self):
        return self.raw

    async def json(self):
        return json.loads(self.raw)


class Temp(unittest.TestCase):

    def setUp(self):
        root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(xr_pairing, "FILE", root / "display" / "xr_devices.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clock = Clock()
        self.pairing = XrPairing(clock=self.clock)
        swap = mock.patch.object(xr_pairing, "pairing", self.pairing)
        swap.start()
        self.addCleanup(swap.stop)


class PairingTests(Temp):

    def test_codes_are_single_use_and_tokens_are_hashed(self):
        code = self.pairing.issue("nunzio")["code"]
        token = self.pairing.redeem(code, "device-1234", "Quest <script>")
        self.assertEqual(self.pairing.authenticate(token), "device-1234")
        with self.assertRaises(PermissionError):
            self.pairing.redeem(code, "device-1234", "again")
        saved = xr_pairing.FILE.read_text(encoding="utf-8")
        self.assertNotIn(token, saved)
        self.assertEqual(stat.S_IMODE(xr_pairing.FILE.stat().st_mode), 0o600)
        device = self.pairing.listing()[0]
        self.assertNotIn("token", device)
        self.assertEqual((device["approver"], device["name"]), ("nunzio", "Quest script"))

    def test_codes_and_tokens_expire(self):
        code = self.pairing.issue("nunzio")["code"]
        self.clock.t += xr_pairing.CODE_TTL + 1
        with self.assertRaises(PermissionError):
            self.pairing.redeem(code, "device-1234", "x")
        token = self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        self.clock.t += xr_pairing.TOKEN_TTL + 1
        self.assertIsNone(self.pairing.authenticate(token))

    def test_revocation_closes_access(self):
        token = self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        self.pairing.revoke("device-1234")
        self.assertIsNone(self.pairing.authenticate(token))
        with self.assertRaises(KeyError):
            self.pairing.revoke("device-1234")

    def test_brute_force_locks_pairing(self):
        code = self.pairing.issue("nunzio")["code"]
        for n in range(xr_pairing.MAX_FAILURES):
            with self.assertRaises(PermissionError):
                self.pairing.redeem(f"{n:08d}x", "device-1234", "x")
        with self.assertRaises(PermissionError) as caught:
            self.pairing.redeem(code, "device-1234", "x")
        self.assertEqual(str(caught.exception), "pairing_locked")

    def test_bad_input_is_refused(self):
        code = self.pairing.issue("nunzio")["code"]
        for device in ("short", "../../etc/passwd", "x" * 65):
            with self.assertRaises(ValueError):
                self.pairing.redeem(code, device, "x")
        for token in (None, "", "x" * 500, "nope"):
            self.assertIsNone(self.pairing.authenticate(token))


class ApiTests(Temp):

    def test_redeem_sets_a_strict_cookie(self):
        code = asyncio.run(xr_api.xr_pair("nunzio"))["code"]
        response = asyncio.run(xr_api.xr_redeem(Request({"code": code, "device": "device-1234"})))
        cookie = response.headers["set-cookie"]
        for part in ("nuxiva_xr=", "HttpOnly", "SameSite=strict", "Secure"):
            self.assertIn(part, cookie)
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(xr_api.xr_redeem(Request({"code": code, "device": "device-1234"})))
        self.assertEqual(caught.exception.status_code, 403)

    def test_scene_needs_a_paired_headset(self):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(xr_api.xr_scene(Request()))
        self.assertEqual(caught.exception.status_code, 401)

    def test_scene_shows_only_the_nucleus_without_authorized_people(self):
        token = self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        from agenti.desktop import presence_bridge
        with mock.patch.dict(presence_bridge.bridge.last, {"kind": "guest_only"}):
            scene = asyncio.run(xr_api.xr_scene(Request(cookies={xr_pairing.COOKIE: token})))
        self.assertEqual((scene["nucleus_only"], scene["panels"]), (True, []))

    def test_scene_lists_allowed_panels_for_authorized_people(self):
        token = self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        items = [{"key": "molecule:a", "id": "molecule_viewer", "name": "Molecola", "icon": "🧬", "data": {"id": "0123456789abcdef"}},
                 {"key": "secret", "id": "notes", "name": "Note", "icon": "📝", "sensitivity": "private"}]
        from agenti.desktop import presence_bridge
        from agenti.desktop.desk import desk
        with mock.patch.dict(presence_bridge.bridge.last, {"kind": "authorized"}), mock.patch.object(desk, "active", return_value=items):
            scene = asyncio.run(xr_api.xr_scene(Request(cookies={xr_pairing.COOKIE: token})))
        self.assertFalse(scene["nucleus_only"])
        self.assertEqual(scene["panels"][0]["molecule"], "0123456789abcdef")

    def test_room_updates_are_validated(self):
        self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        result = asyncio.run(xr_api.xr_device_update("device-1234", Request({"room": "Studio"}), "admin"))
        self.assertEqual(result["room"], "studio")
        with self.assertRaises(HTTPException):
            asyncio.run(xr_api.xr_device_update("device-1234", Request({"room": "!!!"}), "admin"))
        with self.assertRaises(HTTPException):
            asyncio.run(xr_api.xr_device_update("unknown-device", Request({"room": "a"}), "admin"))

    def test_paired_headset_counts_as_display(self):
        import access
        token = self.pairing.redeem(self.pairing.issue("nunzio")["code"], "device-1234", "x")
        request = mock.Mock(cookies={xr_pairing.COOKIE: token})
        self.assertTrue(access.paired_display(request))
        request.cookies = {}
        self.assertFalse(access.paired_display(request))
