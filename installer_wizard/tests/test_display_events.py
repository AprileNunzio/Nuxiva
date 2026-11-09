import json
import unittest
from unittest import mock

from starlette.requests import Request
from fastapi import HTTPException

import display_events
import snapshot
from features.desktop.camera_sessions import MAX_PER_LOGIN, TTL_SECONDS, CameraSessions, camera_owner
from features.desktop.display_scope import is_host_display, remote_display_scope, remote_state
from features.vision.remote_frame import CONTENT_TYPE, FRAME_BYTES, read_frame
from state import store


class DisplayEventsTests(unittest.TestCase):

    def setUp(self):
        self.events = display_events.DisplayEvents()

    def test_every_client_receives_the_same_event(self):
        first = second = self.events.cursor()
        self.events.push("holo_action", {"express": "smile"})
        self.assertEqual([e.payload for e in self.events.since(first)], [{"express": "smile"}])
        self.assertEqual([e.payload for e in self.events.since(second)], [{"express": "smile"}])

    def test_events_expire(self):
        start = self.events.cursor()
        self.events.push("holo_action", {"play": "balla"}, ttl=1.0)
        self.assertEqual(self.events.since(start, now=10 ** 12), [])

    def test_pushing_wakes_the_stream(self):
        before = store.version
        self.events.push("holo_action", {"tint": "blu"})
        self.assertGreater(store.version, before)

    def test_holo_helper_drops_empty_values(self):
        with mock.patch.object(display_events, "events", self.events):
            display_events.holo({"express": "smile", "play": None, "tint": ""})
        self.assertEqual(self.events.since(0)[-1].payload, {"express": "smile"})


class SharedSnapshotTests(unittest.TestCase):

    def setUp(self):
        snapshot._shared.clear()

    def test_clients_share_one_build_per_version(self):
        with mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}) as build:
            first = snapshot.shared_snapshot(False)
            second = snapshot.shared_snapshot(False)
        self.assertEqual(build.call_count, 1)
        self.assertIs(first[1], second[1])

    def test_a_new_version_rebuilds(self):
        with mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}) as build:
            snapshot.shared_snapshot(False)
            store.touch()
            snapshot.shared_snapshot(False)
        self.assertEqual(build.call_count, 2)

    def test_two_screens_both_get_the_holographic_action(self):
        events = display_events.DisplayEvents()
        with mock.patch.object(display_events, "events", events), \
                mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}):
            screen_a = screen_b = events.cursor()
            events.push("holo_action", {"express": "smile"})
            text_a, screen_a = snapshot.frame(False, screen_a)
            text_b, screen_b = snapshot.frame(False, screen_b)
            again, _ = snapshot.frame(False, screen_a)
        self.assertEqual(json.loads(text_a)["holo_action"], {"express": "smile"})
        self.assertEqual(json.loads(text_b)["holo_action"], {"express": "smile"})
        self.assertNotIn("holo_action", json.loads(again))

    def test_remote_snapshot_and_both_stream_formats_exclude_host_presence(self):
        events = display_events.DisplayEvents()
        private = {
            "phase": "READY",
            "presence": {"people": [{"name": "Owner"}]},
            "audience": {"kind": "authorized"},
            "greeting": {"names": ["Owner"]},
            "desk": [{"data": "private payload"}],
        }
        with mock.patch.object(display_events, "events", events), \
                mock.patch.object(snapshot, "full_snapshot", return_value=private), \
                mock.patch.object(store, "snapshot", return_value=private):
            cursor = events.cursor()
            events.push("holo_action", {"play": "private event"})
            host, _ = snapshot.frame(False, cursor)
            remote, _ = snapshot.frame(False, cursor, remote=True)
            delta, _, _ = snapshot.delta_frame(False, None, cursor, remote=True)
            public, _ = snapshot.shared_snapshot(False, remote=True)

        self.assertEqual(public["phase"], "READY")
        self.assertEqual(public["audience"]["kind"], "uncertain")
        self.assertEqual(public["presence"]["people"], [])
        self.assertIsNone(public["greeting"])
        self.assertEqual(public["desk"], [])
        for payload in (remote, delta):
            for secret in ("Owner", "private payload", "private event"):
                self.assertNotIn(secret, payload)
        self.assertIn("private event", host)

    def test_only_direct_loopback_requests_share_the_host_display_scope(self):
        def request(peer, host, forwarded=None):
            headers = [(b"host", host)]
            if forwarded:
                headers.append((b"x-forwarded-for", forwarded))
            return Request({"type": "http", "scheme": "http", "path": "/", "headers": headers,
                            "client": (peer, 50000), "server": ("127.0.0.1", 8080)})

        self.assertTrue(is_host_display(request("127.0.0.1", b"localhost:8080")))
        self.assertFalse(is_host_display(request("192.168.1.20", b"localhost:8080")))
        self.assertFalse(is_host_display(request("127.0.0.1", b"nuxiva.local")))
        self.assertFalse(is_host_display(request("127.0.0.1", b"localhost:8080", b"192.168.1.20")))

    def test_remote_state_keeps_public_progress_without_host_details(self):
        state = remote_state(
            {"components": {"vision": {"label": "Vision", "status": "ok", "detail": "private"}}},
            {"progress": 30, "items": [{"id": "vision", "progress": 30, "message": "private"}],
             "waiting_reason": "private"},
            {"style": "character", "custom_model": "/private"},
        )
        self.assertEqual(state["components"], {"vision": {"label": "Vision", "status": "ok"}})
        self.assertEqual(state["background"], {"progress": 30, "items": [{"id": "vision", "progress": 30}]})
        self.assertEqual(state["face"], {"style": "character"})
        self.assertEqual(state["sounds"], {"enabled": False, "cues": []})

    def test_headless_lan_browser_scope_requires_disabled_protection(self):
        def request(peer, extra=()):
            return Request({"type": "http", "scheme": "http", "path": "/",
                            "headers": [(b"host", b"192.168.1.197"), *extra],
                            "client": (peer, 50000), "server": ("192.168.1.197", 80)})

        with (
            mock.patch("features.desktop.display_scope.env_get", return_value="0") as kiosk,
            mock.patch("features.desktop.display_scope.gate_enabled", return_value=False) as gate,
        ):
            self.assertEqual(remote_display_scope(request("192.168.1.20")), "browser")
            self.assertEqual(remote_display_scope(request("127.0.0.1")), "browser")
            self.assertIs(remote_display_scope(request("8.8.8.8")), True)
            self.assertIs(remote_display_scope(request("192.168.1.20", [(b"forwarded", b"for=10.0.0.1")])), True)
            gate.return_value = True
            self.assertIs(remote_display_scope(request("192.168.1.20")), True)
            gate.return_value = False
            kiosk.return_value = "1"
            self.assertIs(remote_display_scope(request("192.168.1.20")), True)

    def test_browser_widgets_do_not_share_host_state_or_events(self):
        events = display_events.DisplayEvents()
        with (
            mock.patch.object(display_events, "events", events),
            mock.patch.object(store, "snapshot", return_value={
                "phase": "READY", "desk": [{"id": "clock", "data": {"secret": "host-private"}}],
                "presence": {"people": [{"name": "host-private"}]},
            }),
            mock.patch.dict(snapshot._shared, clear=True),
        ):
            cursor = events.cursor()
            events.push("holo_action", {"text": "host-private"})
            browser, _ = snapshot.shared_snapshot(False, remote="browser")
            protected, _ = snapshot.shared_snapshot(False, remote=True)
            legacy, _ = snapshot.frame(False, cursor, remote="browser")
            delta, _, _ = snapshot.delta_frame(False, None, cursor, remote="browser")
        self.assertEqual([widget["id"] for widget in browser["desk"]], ["clock", "calculator"])
        self.assertEqual(browser["audience"]["kind"], "guest_only")
        self.assertFalse(browser["audience"]["gate"])
        self.assertEqual(protected["desk"], [])
        for payload in (legacy, delta):
            self.assertNotIn("host-private", payload)


class CameraSessionTests(unittest.TestCase):
    def test_lease_is_bound_to_its_owner_and_can_be_revoked(self):
        sessions = CameraSessions()
        first, second = sessions.issue("first"), sessions.issue("second")
        self.assertFalse(sessions.update(first, "second"))
        self.assertFalse(sessions.update(first, "second", revoke=True))
        self.assertTrue(sessions.update(first, "first", revoke=True))
        self.assertFalse(sessions.update(first, "first"))
        self.assertTrue(sessions.update(second, "second"))

    def test_expired_lease_cannot_be_reopened_and_releases_capacity(self):
        clock = mock.Mock(return_value=0.0)
        sessions = CameraSessions(clock)
        tokens = [sessions.issue("owner") for _ in range(MAX_PER_LOGIN)]
        with self.assertRaises(HTTPException) as error:
            sessions.issue("owner")
        self.assertEqual(error.exception.status_code, 429)
        clock.return_value = TTL_SECONDS / 2
        self.assertTrue(sessions.update(tokens[0], "owner"))
        clock.return_value = TTL_SECONDS
        self.assertTrue(sessions.update(tokens[0], "owner"))
        self.assertFalse(sessions.update(tokens[1], "owner"))
        self.assertTrue(sessions.issue("owner"))

    def test_camera_request_requires_an_authorized_same_origin_https_session(self):
        def request(origin, scheme="https"):
            return Request({
                "type": "http", "scheme": scheme, "path": "/", "server": ("nuxiva.test", 443),
                "headers": [(b"host", b"nuxiva.test"), (b"origin", origin), (b"x-nuxiva-request", b"1")],
            })

        with mock.patch("features.desktop.camera_sessions.session_user", return_value=None), \
                mock.patch("features.desktop.camera_sessions.display_node", return_value=None):
            for origin, scheme, expected in (
                (b"https://other.test", "https", 403),
                (b"https://nuxiva.test", "http", 403),
                (b"https://nuxiva.test", "https", 401),
            ):
                with self.assertRaises(HTTPException) as error:
                    camera_owner(request(origin, scheme))
                self.assertEqual(error.exception.status_code, expected)

    def test_frame_admission_is_rate_limited_across_renewal(self):
        clock = mock.Mock(return_value=0.0)
        sessions = CameraSessions(clock)
        token = sessions.issue("owner")
        sessions.admit_frame(token, "owner")
        self.assertTrue(sessions.update(token, "owner"))
        with self.assertRaises(HTTPException) as limited:
            sessions.admit_frame(token, "owner")
        self.assertEqual(limited.exception.status_code, 429)
        clock.return_value = 1.0
        sessions.admit_frame(token, "owner")
        with self.assertRaises(HTTPException) as denied:
            sessions.admit_frame(token, "another-login")
        self.assertEqual(denied.exception.status_code, 404)


class RemoteFrameTests(unittest.IsolatedAsyncioTestCase):
    async def test_headless_lan_state_and_both_streams_render_browser_widgets(self):
        from system_api import public_state

        request = Request({"type": "http", "scheme": "http", "path": "/api/state",
                           "headers": [(b"host", b"192.168.1.197")],
                           "client": ("192.168.1.20", 50000), "server": ("192.168.1.197", 80)})
        with (
            mock.patch("features.desktop.display_scope.env_get", return_value="0"),
            mock.patch("features.desktop.display_scope.gate_enabled", return_value=False) as gate,
            mock.patch.object(request, "is_disconnected", new=mock.AsyncMock(return_value=False)),
            mock.patch.dict(snapshot._shared, clear=True),
        ):
            public = await public_state(request)
            self.assertEqual([widget["id"] for widget in json.loads(public.body)["desk"]], ["clock", "calculator"])
            for endpoint in (snapshot.sse, snapshot.sse_delta):
                response = await endpoint(admin=False)(request)
                try:
                    first = await anext(response.body_iterator)
                    self.assertIn("browser:clock", first)
                    gate.return_value = True
                    next_frame = await anext(response.body_iterator)
                    self.assertNotIn("browser:clock", next_frame)
                    self.assertRegex(next_frame, r'"nucleus_only":\s*true')
                    gate.return_value = False
                finally:
                    await response.body_iterator.aclose()

    async def test_accepts_only_complete_bounded_raw_frames(self):
        def request(data, size=FRAME_BYTES, content_type=CONTENT_TYPE):
            async def receive():
                return {"type": "http.request", "body": data, "more_body": False}
            return Request({"type": "http", "headers": [
                (b"content-type", content_type.encode()), (b"content-length", str(size).encode()),
            ]}, receive)

        frame = bytes(FRAME_BYTES)
        self.assertEqual(await read_frame(request(frame)), frame)
        for invalid, code in (
            (request(frame, content_type="image/jpeg"), 415),
            (request(frame, size=0), 413),
            (request(frame + b"0"), 413),
            (request(frame[:-1]), 400),
        ):
            with self.assertRaises(HTTPException) as error:
                await read_frame(invalid)
            self.assertEqual(error.exception.status_code, code)


if __name__ == "__main__":
    unittest.main()
