import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agenti.nodes import adapt, zt_engine
from agenti.nodes import enrollment as enrollment_module
from agenti.rpa import android_enroll, android_pairing, android_release, releases

BASE = f"https://github.com/{releases.REPOSITORY}/releases/download"
DIGEST = "sha256:" + "ab" * 32
KOTLIN_PUBLIC = "03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8"
KOTLIN_SIGNATURE = ("6a58ada4483ff467842b6f3eac35bd7ac989968554321adc4dfe7d9d89ed25030f919a422aa1bd934098829e77a3031d"
                    "0ec8d70355646c04b7e10773f975170b")


def release(tag, name=android_release.APK, digest=DIGEST, **extra):
    asset = {"name": name, "browser_download_url": f"{BASE}/{tag}/{name}"}
    if digest:
        asset["digest"] = digest
    return {"tag_name": tag, "assets": [asset], **extra}


class ReleaseTest(unittest.TestCase):
    def test_newest_published_apk_is_chosen(self):
        chosen = android_release.newest([release("android-v5.8.1"), release("android-v5.10.0"), release("other-v9.0.0"),
                                         release("android-v6.0.0", draft=True), release("android-v7.0.0", name="other.apk")])
        self.assertEqual((chosen["version"], chosen["sha256"]), ("5.10.0", "ab" * 32))
        self.assertNotIn("key", chosen)

    def test_apk_without_a_digest_or_from_a_foreign_host_is_rejected(self):
        self.assertEqual(android_release.newest([release("android-v5.8.1", digest="")]), {})
        foreign = {"tag_name": "android-v5.8.1", "assets": [{"name": android_release.APK, "digest": DIGEST,
                                                              "browser_download_url": "https://evil.example/a.apk"}]}
        self.assertEqual(android_release.newest([foreign]), {})


class KotlinCompatibilityTest(unittest.TestCase):
    def test_signature_made_on_the_phone_verifies_on_the_server(self):
        body = b'{"a":1}'
        zt_engine.verify_request(KOTLIN_PUBLIC, KOTLIN_SIGNATURE, "android-test-ab12cd", "POST", "/api/nodes/heartbeat?x=1",
                                 1760000000, "00112233445566778899aabbccddeeff", hashlib.sha256(body).hexdigest(), 1760000000)

    def test_a_tampered_body_is_rejected(self):
        with self.assertRaises(ValueError):
            zt_engine.verify_request(KOTLIN_PUBLIC, KOTLIN_SIGNATURE, "android-test-ab12cd", "POST", "/api/nodes/heartbeat?x=1",
                                     1760000000, "00112233445566778899aabbccddeeff", hashlib.sha256(b"{}").hexdigest(), 1760000000)


class EnrollmentLinkTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        patches = [mock.patch.object(enrollment_module, "TOKENS_FILE", directory / "tokens.json"),
                   mock.patch.object(android_enroll.trust, "ca_pin", return_value="a" * 64),
                   mock.patch.dict(android_enroll.secure._active, {"port": 8443}),
                   mock.patch.object(android_enroll.android_release, "info", mock.AsyncMock(return_value={"version": "5.8.2", "name": "Nuxiva.apk", "url": f"{BASE}/android-v5.8.2/Nuxiva.apk", "sha256": "ab" * 32}))]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.tokens = enrollment_module.EnrollmentTokens.__new__(enrollment_module.EnrollmentTokens)
        self.tokens.items = {}
        patcher = mock.patch.object(android_enroll, "tokens", self.tokens)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.pairings = android_pairing.Pairings()
        patcher = mock.patch.object(android_enroll, "pairings", self.pairings)
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(android_enroll.admin_routes)
        app.include_router(android_enroll.public_routes)
        app.dependency_overrides[android_enroll.require_admin] = lambda: "admin"
        self.client = TestClient(app, base_url="https://192.168.1.10")

    def test_link_carries_a_short_lived_single_use_pinned_payload(self):
        response = self.client.post("/api/android/enrollment")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        link = response.json()["link"]
        self.assertTrue(link.startswith("nuxiva://enroll?d="))
        encoded = link.split("=", 1)[1]
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        self.assertEqual((payload["server"], payload["pin"]), ("https://192.168.1.10:8443", "a" * 64))
        self.assertLessEqual(payload["expires"] - __import__("time").time(), android_enroll.LIFETIME + 2)
        self.assertTrue(self.tokens.verify(payload["token"]))
        self.assertLess(len(link), 2000)

    def test_refused_without_https_a_release_or_from_localhost(self):
        with mock.patch.dict(android_enroll.secure._active, {"port": 0}):
            self.assertEqual(self.client.post("/api/android/enrollment").json()["detail"], "enroll_https_unavailable")
        self.assertEqual(TestClient(self.client.app, base_url="https://127.0.0.1").post("/api/android/enrollment").status_code, 409)
        with mock.patch.object(android_enroll.android_release, "info", mock.AsyncMock(return_value={})):
            self.assertEqual(self.client.post("/api/android/enrollment").json()["detail"], "android_apk_unavailable")

    def test_six_digit_code_returns_the_same_payload_once(self):
        made = self.client.post("/api/android/enrollment").json()
        self.assertRegex(made["code"], r"^\d{6}$")
        self.assertEqual(made["fingerprint"], "A" * 16)
        got = self.client.post("/api/android/enrollment-code", json={"code": made["code"]})
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["server"], "https://192.168.1.10:8443")
        self.assertTrue(self.tokens.verify(got.json()["token"]))
        again = self.client.post("/api/android/enrollment-code", json={"code": made["code"]})
        self.assertEqual((again.status_code, again.json()["detail"]), (403, "enroll_code_invalid"))
        self.assertEqual(self.client.get(f"/api/android/enrollment/{made['id']}").json()["state"], "code_used")

    def test_wrong_codes_are_rate_limited_per_address(self):
        self.client.post("/api/android/enrollment")
        codes = [self.client.post("/api/android/enrollment-code", json={"code": "000000"}).status_code for _ in range(7)]
        self.assertEqual(codes[:5], [403] * 5)
        self.assertEqual(codes[5:], [429, 429])

    def test_global_failure_burst_invalidates_every_pending_code(self):
        made = self.client.post("/api/android/enrollment").json()
        for index in range(android_pairing.GLOBAL_LIMIT):
            self.pairings.failures.clear()
            self.client.post("/api/android/enrollment-code", json={"code": "00000" + str(index % 10)})
        self.pairings.failures.clear()
        self.pairings.global_failures.clear()
        self.assertEqual(self.client.post("/api/android/enrollment-code", json={"code": made["code"]}).status_code, 403)

    def test_malformed_code_is_rejected(self):
        self.client.post("/api/android/enrollment")
        for bad in ("12345", "1234567", "abcdef", "١٢٣٤٥٦", ""):
            self.assertEqual(self.client.post("/api/android/enrollment-code", json={"code": bad}).status_code, 403)

    def test_revoke_burns_token_and_code(self):
        made = self.client.post("/api/android/enrollment").json()
        token = json.loads(base64.urlsafe_b64decode(made["link"].split("=", 1)[1] + "==="))["token"]
        self.assertEqual(self.client.delete(f"/api/android/enrollment/{made['id']}").status_code, 200)
        self.assertFalse(self.tokens.alive(token))
        self.assertEqual(self.client.post("/api/android/enrollment-code", json={"code": made["code"]}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/android/enrollment/{made['id']}").status_code, 404)

    def test_enrolled_state_after_token_is_consumed(self):
        made = self.client.post("/api/android/enrollment").json()
        token = json.loads(base64.urlsafe_b64decode(made["link"].split("=", 1)[1] + "==="))["token"]
        self.tokens.revoke(token)
        self.assertEqual(self.client.get(f"/api/android/enrollment/{made['id']}").json()["state"], "enrolled")

    def test_active_pairings_are_capped(self):
        for _ in range(android_pairing.MAX_ACTIVE):
            self.assertEqual(self.client.post("/api/android/enrollment").status_code, 200)
        self.assertEqual(self.client.post("/api/android/enrollment").status_code, 429)

    def test_installer_info_reports_the_release(self):
        self.assertEqual(self.client.get("/api/android/installer-info").json()["version"], "5.8.2")


class HardwareTest(unittest.TestCase):
    def test_phone_hardware_is_whitelisted_and_bounded(self):
        clean = adapt.clean_hardware({
            "cores": 8, "ram_gb": 7.7, "model": "Google Pixel 8 <b>", "sensors": ["accelerometer"] * 40 + [""],
            "display": {"width": 1080, "height": 2400, "dpi": 420, "hz": 120, "evil": 1},
            "orientation": {"mode": "landscape", "rotation": 90, "turn": "ccw"}})
        self.assertEqual(clean["model"], "Google Pixel 8 b")
        self.assertEqual(len(clean["sensors"]), adapt.MAX_SENSORS)
        self.assertEqual(clean["display"], {"width": 1080, "height": 2400, "dpi": 420, "hz": 120})
        self.assertEqual(clean["orientation"], {"mode": "landscape", "rotation": 90, "turn": "ccw"})

    def test_invalid_orientation_is_dropped(self):
        for bad in ({"mode": "x", "rotation": 90}, {"mode": "portrait", "rotation": 45}, "text", None):
            self.assertEqual(adapt.clean_orientation(bad), {})
        self.assertEqual(adapt.clean_orientation({"mode": "portrait", "rotation": 0, "turn": "spin"})["turn"], "none")

    def test_orientation_change_is_reported(self):
        old = adapt.clean_hardware({"cores": 8, "orientation": {"mode": "portrait", "rotation": 0}})
        new = adapt.clean_hardware({"cores": 8, "orientation": {"mode": "landscape", "rotation": 90, "turn": "ccw"}})
        self.assertIn("Orientamento: landscape", adapt.diff(old, new))


if __name__ == "__main__":
    unittest.main()


class ContractTest(unittest.TestCase):
    FIXTURE = Path(__file__).resolve().parents[2] / "contracts" / "android_enrollment.json"

    def test_server_links_match_the_shared_fixture_read_by_the_app(self):
        data = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        self.assertTrue(data["cases"])
        for case in data["cases"]:
            self.assertEqual(android_enroll.enrollment_link(case["payload"]), case["link"], case["name"])
            self.assertEqual(set(case["payload"]), {"server", "token", "pin", "expires"})
            self.assertIsInstance(case["payload"]["expires"], int)

    def test_origin_brackets_ipv6_hosts(self):
        from agenti.nodes import trust
        self.assertEqual(trust.https_origin("fe80::1234", 8443), "https://[fe80::1234]:8443")
        self.assertEqual(trust.https_origin("nuxiva.local", 443), "https://nuxiva.local")

    def test_previous_asset_name_is_still_offered_until_a_new_release_exists(self):
        old = release("android-v5.8.3", name=android_release.LEGACY_APK)
        self.assertEqual(android_release.newest([old])["name"], android_release.LEGACY_APK)
        both = {"tag_name": "android-v5.8.4", "assets": release("android-v5.8.4")["assets"]}
        self.assertEqual(android_release.newest([old, both])["name"], android_release.APK)
