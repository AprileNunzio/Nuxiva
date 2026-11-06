import unittest
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_cloud
from tests.test_setup_wizard import HEADERS, Network

KEY = "sk-" + "a" * 40


class SetupCloudTest(unittest.TestCase):
    def setUp(self):
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        self.addCleanup(setup_api.SETUP_FILE.unlink, missing_ok=True)
        setup_cloud._gate["at"] = 0.0
        self.public = TestClient(nuxiva_supervisor.public, base_url="http://127.0.0.1")

    def post(self, body):
        setup_cloud._gate["at"] = 0.0
        return self.public.post("/api/setup/cloud/test", json=body, headers=HEADERS)

    def test_every_offered_provider_is_accepted_by_the_setup(self):
        for pid in ("anthropic", "gemini", "openai", "mistral", "groq", "openrouter"):
            self.assertIn(pid, setup_api.CLOUD_PICK)
            self.assertEqual(setup_api.cloud_choice({"cloud_provider": pid, "cloud_key": KEY})[0], pid)

    def test_the_key_is_really_checked(self):
        with Network(local=True), mock.patch.object(setup_cloud, "_probe", return_value=True) as probe:
            res = self.post({"cloud_provider": "anthropic", "cloud_key": KEY})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True})
        probe.assert_awaited_once_with("anthropic", KEY)
        with Network(local=True), mock.patch.object(setup_cloud, "_probe", return_value=False):
            self.assertEqual(self.post({"cloud_provider": "anthropic", "cloud_key": KEY}).json(), {"ok": False})

    def test_invalid_input_is_refused_before_any_network_call(self):
        with Network(local=True), mock.patch.object(setup_cloud, "_probe") as probe:
            self.assertEqual(self.post({"cloud_provider": "evil", "cloud_key": KEY}).status_code, 400)
            self.assertEqual(self.post({"cloud_provider": "openai", "cloud_key": "short"}).status_code, 400)
        probe.assert_not_called()

    def test_outside_the_home_network_is_refused(self):
        with Network(local=False, private=False):
            self.assertEqual(self.post({"cloud_provider": "openai", "cloud_key": KEY}).status_code, 403)

    def test_requests_are_throttled(self):
        with Network(local=True), mock.patch.object(setup_cloud, "_probe", return_value=True):
            self.assertEqual(self.post({"cloud_provider": "openai", "cloud_key": KEY}).status_code, 200)
            again = self.public.post("/api/setup/cloud/test", json={"cloud_provider": "openai", "cloud_key": KEY},
                                     headers=HEADERS)
        self.assertEqual(again.status_code, 429)


if __name__ == "__main__":
    unittest.main()
