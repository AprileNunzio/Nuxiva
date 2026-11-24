import importlib.util
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

import snapshot
from agenti.desktop import display_scope
from agenti.desktop import remote_presence as presence_module
from agenti.desktop.remote_presence import (
    liveness_for, probe_kind,
    OUTCOMES, TTL_SECONDS, RemotePresence, judge, probe_session, viewer,
)

ROOT = Path(__file__).resolve().parents[1]
VISION = ROOT / "agenti" / "percezione" / "vision"
DISPLAY = ROOT / "web" / "display"


def load_verdict():
    spec = importlib.util.spec_from_file_location("remote_verdict_under_test", VISION / "remote_verdict.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verdict = load_verdict()


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Tracker:
    def __init__(self, states) -> None:
        self.states = list(states)

    def update(self, points, now, minimum) -> dict:
        return {"state": self.states.pop(0) if self.states else "unknown"}


def https_request(cookie: str | None = "token", client: str = "192.168.1.20") -> Request:
    scope = {"type": "http", "method": "GET", "scheme": "https", "path": "/api/state",
             "headers": [(b"host", b"172.17.89.72")], "client": (client, 50000)}
    request = Request(scope)
    request._cookies = {"nuxiva_session": cookie} if cookie else {}
    return request


class FaceOutcomeTest(unittest.TestCase):
    def test_rejects_empty_crowded_and_small_frames(self):
        self.assertEqual(verdict.face_outcome(None), "no_face")
        self.assertEqual(verdict.face_outcome([]), "no_face")
        self.assertEqual(verdict.face_outcome([[0, 0, 80, 80], [10, 10, 80, 80]]), "many_faces")
        self.assertEqual(verdict.face_outcome([[0, 0, 30, 80]]), "small_face")
        self.assertIsNone(verdict.face_outcome([[0, 0, verdict.MIN_FACE_PX, verdict.MIN_FACE_PX]]))

    def test_identity_outcomes_explain_the_reason(self):
        self.assertEqual(verdict.identity_outcome({"slug": "nunzio"}, 0, "unknown")["outcome"], "no_gallery")
        self.assertEqual(verdict.identity_outcome({"slug": None, "ambiguous": True}, 2, "unknown")["outcome"], "ambiguous")
        self.assertEqual(verdict.identity_outcome({"slug": None}, 2, "unknown")["outcome"], "unknown")
        matched = verdict.identity_outcome({"slug": "nunzio", "name": "N" * 200}, 2, "live")
        self.assertEqual(matched["outcome"], "matched")
        self.assertEqual(matched["slug"], "nunzio")
        self.assertEqual(len(matched["name"]), verdict.NAME_LIMIT)
        self.assertEqual(matched["liveness"], "live")


class LivenessBookTest(unittest.TestCase):
    def test_tracks_each_session_and_rejects_malformed_ids(self):
        clock = Clock()
        book = verdict.LivenessBook(lambda: Tracker(["unknown", "live"]), clock)
        session = probe_session("a" * 43)
        self.assertEqual(book.update("bad", [0.0] * 10, 0.0, 0.55), "unknown")
        self.assertEqual(len(book), 0)
        self.assertEqual(book.update(session, [0.0] * 10, 0.0, 0.55), "unknown")
        self.assertEqual(book.update(session, [0.0] * 10, 1.0, 0.55), "live")
        clock.now += verdict.SESSION_TTL + 1
        self.assertEqual(book.update(session, [0.0] * 10, 2.0, 0.55), "unknown")

    def test_caps_sessions(self):
        book = verdict.LivenessBook(lambda: Tracker([]), Clock())
        for index in range(verdict.MAX_SESSIONS + 5):
            book.update(probe_session(str(index)), [0.0] * 10, 0.0, 0.55)
        self.assertEqual(len(book), verdict.MAX_SESSIONS)


class JudgeTest(unittest.TestCase):
    def matched(self, liveness="unknown"):
        return {"outcome": "matched", "slug": "nunzio", "name": "Nunzio", "liveness": liveness}

    def test_owner_is_granted_in_advisory_mode(self):
        self.assertEqual(judge(self.matched(), "owner", "advisory"),
                         {"outcome": "matched", "slug": "nunzio", "name": "Nunzio"})

    def test_guest_role_is_not_authorized(self):
        self.assertEqual(judge(self.matched(), "guest", "advisory")["outcome"], "not_authorized")

    def test_spoof_is_denied_unless_liveness_off(self):
        self.assertEqual(judge(self.matched("spoof"), "owner", "advisory")["outcome"], "spoof")
        self.assertEqual(judge(self.matched("spoof"), "owner", "off")["outcome"], "matched")

    def test_strict_mode_requires_live_face(self):
        self.assertEqual(judge(self.matched(), "owner", "strict")["outcome"], "liveness_needed")
        self.assertEqual(judge(self.matched("live"), "family", "strict")["outcome"], "matched")

    def test_malformed_payload_is_unavailable(self):
        self.assertEqual(judge(None, "", "advisory"), {"outcome": "unavailable"})
        self.assertEqual(judge({"outcome": "<script>"}, "", "advisory"), {"outcome": "unavailable"})
        self.assertEqual(judge({"outcome": "no_face"}, "", "advisory"), {"outcome": "no_face"})


class RemotePresenceTest(unittest.TestCase):
    def test_match_grants_a_short_lease_bound_to_the_viewer(self):
        clock = Clock()
        presence = RemotePresence(clock)
        reply = presence.settle("viewer-a", {"outcome": "matched", "slug": "nunzio", "name": "Nunzio"})
        self.assertEqual(reply, {"outcome": "matched", "name": "Nunzio"})
        self.assertEqual(presence.holder("viewer-a"), "nunzio")
        self.assertIsNone(presence.holder("viewer-b"))
        clock.now += TTL_SECONDS + 0.1
        self.assertIsNone(presence.holder("viewer-a"))

    def test_stranger_or_crowd_revokes_but_a_missing_face_keeps_the_lease(self):
        presence = RemotePresence(Clock())
        presence.settle("viewer-a", {"outcome": "matched", "slug": "nunzio", "name": ""})
        presence.settle("viewer-a", {"outcome": "no_face"})
        self.assertEqual(presence.holder("viewer-a"), "nunzio")
        presence.settle("viewer-a", {"outcome": "many_faces"})
        self.assertIsNone(presence.holder("viewer-a"))

    def test_match_without_viewer_is_not_granted(self):
        presence = RemotePresence(Clock())
        self.assertEqual(presence.settle(None, {"outcome": "matched", "slug": "nunzio", "name": ""}),
                         {"outcome": "unavailable"})


class ViewerScopeTest(unittest.TestCase):
    def test_viewer_requires_https_and_a_signed_in_user(self):
        with patch("agenti.desktop.remote_presence.session_user", return_value="nunzio"):
            self.assertRegex(viewer(https_request()), r"^[0-9a-f]{64}$")
            self.assertNotEqual(viewer(https_request("one")), viewer(https_request("two")))
        with patch("agenti.desktop.remote_presence.session_user", return_value=None), \
                patch.object(presence_module, "_kiosk", return_value=False):
            self.assertIsNone(viewer(https_request()))

    def test_recognized_viewer_gets_the_authorized_scope(self):
        presence = RemotePresence(Clock())
        with patch("agenti.desktop.remote_presence.session_user", return_value="nunzio"), \
                patch.object(display_scope, "remote_presence", presence), \
                patch.object(display_scope, "is_host_display", return_value=False):
            request = https_request()
            self.assertNotEqual(display_scope.remote_display_scope(request), "recognized")
            presence.grant(viewer(request), "nunzio")
            self.assertEqual(display_scope.remote_display_scope(request), "recognized")
            self.assertNotEqual(display_scope.remote_display_scope(https_request("other")), "recognized")


class KioskProbeTest(unittest.TestCase):
    def kiosk_request(self, cookie="signed", headers=None):
        request = https_request(None)
        request._cookies = {"nuxiva_display": cookie}
        for name, value in (headers or {}).items():
            request.scope["headers"].append((name.encode(), value.encode()))
        if hasattr(request, "_headers"):
            del request._headers
        return request

    def test_probe_is_on_by_default_for_admins_and_kiosk_viewers(self):
        with patch.object(presence_module, "_admin", return_value=True), \
                patch.object(presence_module, "env_get", return_value="1"):
            self.assertEqual(probe_kind(https_request()), "admin")
        with patch.object(presence_module, "_admin", return_value=False), \
                patch.object(presence_module, "_kiosk", return_value=True), \
                patch.object(presence_module, "env_get", return_value="1"):
            self.assertEqual(probe_kind(https_request()), "kiosk")
        with patch.object(presence_module, "_admin", return_value=True), \
                patch.object(presence_module, "env_get", return_value="0"):
            self.assertIsNone(probe_kind(https_request()))

    def test_kiosk_viewer_needs_kiosk_mode_private_network_and_signed_display_cookie(self):
        with patch("agenti.desktop.camera_sessions.is_remote_kiosk_camera_enabled", return_value=True), \
                patch.object(presence_module.auth, "verify", side_effect=lambda value: value == "signed"):
            self.assertTrue(presence_module._kiosk(self.kiosk_request()))
            self.assertFalse(presence_module._kiosk(self.kiosk_request("forged")))
            self.assertFalse(presence_module._kiosk(self.kiosk_request(headers={"x-forwarded-for": "8.8.8.8"})))
            with patch.object(presence_module, "session_user", return_value=None):
                self.assertRegex(viewer(self.kiosk_request()), r"^[0-9a-f]{64}$")
        with patch("agenti.desktop.camera_sessions.is_remote_kiosk_camera_enabled", return_value=False), \
                patch.object(presence_module.auth, "verify", return_value=True):
            self.assertFalse(presence_module._kiosk(self.kiosk_request()))

    def test_kiosk_viewers_always_need_a_live_face(self):
        self.assertEqual(liveness_for("kiosk", "advisory"), "strict")
        self.assertEqual(liveness_for("admin", "advisory"), "advisory")


class RecognizedSnapshotTest(unittest.TestCase):
    def setUp(self):
        snapshot._shared.clear()

    def tearDown(self):
        snapshot._shared.clear()

    def test_recognized_scope_builds_the_authorized_view_separately(self):
        with patch.object(snapshot, "full_snapshot", return_value={"v": 1}) as build:
            snapshot.shared_snapshot(False, remote="recognized")
            snapshot.shared_snapshot(False)
        self.assertEqual(build.call_args_list[0].kwargs, {"recognized": True})
        self.assertEqual(build.call_args_list[1].kwargs, {})

    def test_recognized_audience_opens_the_desk(self):
        audience = snapshot.recognized_audience()
        self.assertEqual(audience["kind"], "authorized")
        self.assertFalse(audience["nucleus_only"])
        self.assertTrue(audience["remote_viewer"])


class ProbeTextsTest(unittest.TestCase):
    def test_every_outcome_and_failure_has_a_text_in_every_language(self):
        script = (DISPLAY / "remote_media" / "probe.js").read_text(encoding="utf-8")
        panel = (DISPLAY / "remote_media" / "panel.js").read_text(encoding="utf-8")
        keys = set(re.findall(r'"(remote_media_probe_[a-z_]+)"', script + panel))
        keys |= {f"remote_media_probe_{outcome}" for outcome in OUTCOMES | {"unavailable"}}
        for language in ("it", "en", "fr", "es"):
            texts = json.loads((DISPLAY / "language" / f"{language}.json").read_text(encoding="utf-8"))["dictionary"]
            self.assertEqual(sorted(keys - texts.keys()), [], language)
            self.assertIn("{{name}}", texts["remote_media_probe_matched"], language)


if __name__ == "__main__":
    unittest.main()
