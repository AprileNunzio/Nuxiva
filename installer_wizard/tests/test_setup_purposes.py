import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_purposes as purposes
import setup_routes
import setup_session
from config import FEATURES_DIR
from features.ear import learner as learner_module
from setup_config import WIZARD_PACKAGES
from setup_session import STEPS, session_manager

HEADERS = {"X-Nuxiva-Request": "1"}


def feature_toggles() -> set[str]:
    found = set()
    for manifest in Path(FEATURES_DIR).glob("*/feature.json"):
        toggle = json.loads(manifest.read_text(encoding="utf-8")).get("toggle") or {}
        if toggle.get("env"):
            found.add(toggle["env"])
    return found


class CatalogueTest(unittest.TestCase):
    def test_every_enabled_key_is_a_real_feature_toggle(self):
        toggles = feature_toggles()
        for pid, spec in purposes.PURPOSES.items():
            for key in spec["enable"]:
                self.assertIn(key, toggles, f"{pid}:{key}")

    def test_every_consent_references_known_things(self):
        for cid, spec in purposes.CONSENTS.items():
            self.assertEqual(set(spec["on"]), set(spec["off"]), cid)
            if spec.get("package"):
                self.assertIn(spec["package"], WIZARD_PACKAGES)
        for pid, spec in purposes.PURPOSES.items():
            self.assertTrue(set(spec["consents"]) <= set(purposes.CONSENTS), pid)
            self.assertTrue(set(spec["packages"]) <= set(WIZARD_PACKAGES), pid)

    def test_sensitive_packages_never_come_without_consent(self):
        sensitive = {spec["package"] for spec in purposes.CONSENTS.values() if spec.get("package")}
        for pid, spec in purposes.PURPOSES.items():
            self.assertFalse(sensitive & set(spec["packages"]), pid)

    def test_every_purpose_asks_about_something_sensitive_or_enables_features(self):
        for pid, spec in purposes.PURPOSES.items():
            self.assertTrue(spec["consents"] or spec["enable"], pid)


class PlanTest(unittest.TestCase):
    def test_unanswered_consents_stay_pending_and_change_nothing(self):
        plan = purposes.build(["security"], {})
        self.assertEqual(set(plan.pending), set(plan.asked))
        self.assertNotIn("NUXIVA_VISION", plan.updates)
        self.assertNotIn("NUXIVA_CAMERAS", plan.updates)

    def test_yes_enables_and_no_disables(self):
        plan = purposes.build(["security"], {"cameras": True, "faces": False, "network_guard": True, "listening": False, "voiceprint": False})
        self.assertEqual(plan.pending, ())
        self.assertEqual(plan.updates["NUXIVA_CAMERAS"], "1")
        self.assertEqual(plan.updates["NUXIVA_VISION"], "0")
        self.assertEqual(plan.updates["NUXIVA_EAR"], "0")
        self.assertIn("vision", plan.denied)
        self.assertNotIn("vision", plan.packages)

    def test_yes_to_listening_adds_its_package(self):
        plan = purposes.build(["home"], {"listening": True})
        self.assertIn("ear", plan.packages)
        self.assertIn("voice", plan.packages)

    def test_skipped_features_are_not_enabled(self):
        plan = purposes.build(["work"], {}, ["NUXIVA_FLEET"])
        self.assertNotIn("NUXIVA_FLEET", plan.updates)
        self.assertIn("NUXIVA_SKILLS", plan.updates)

    def test_consents_of_unchosen_purposes_are_ignored(self):
        plan = purposes.build(["knowledge"], {"faces": True})
        self.assertNotIn("NUXIVA_VISION", plan.updates)

    def test_invalid_input_is_rejected(self):
        for args in ((["nope"], {}), ("home", {}), (["home"], {"unknown": True}), (["home"], {"cameras": "yes"})):
            with self.subTest(args=args), self.assertRaises(purposes.PlanError):
                purposes.build(*args)

    def test_several_purposes_merge_without_duplicates(self):
        plan = purposes.build(["home", "security", "family"], {})
        self.assertEqual(len(plan.asked), len(set(plan.asked)))
        self.assertEqual(len(plan.included), len(set(plan.included)))


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(setup_session, "SESSION_FILE", Path(self.tmp.name) / "session.json"),
                        mock.patch.object(setup_routes, "SAMPLES_DIR", Path(self.tmp.name) / "samples"),
                        mock.patch.object(setup_api, "is_local", lambda r: True),
                        mock.patch.object(setup_api, "_private_client", lambda r: True)]
        for patch in self.patches:
            patch.start()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        session_manager.reset()
        self.public = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        session_manager.reset()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        self.tmp.cleanup()

    def update(self, step, updates):
        return self.public.post("/api/setup/session/update", json={"step": step, "updates": updates}, headers=HEADERS)

    def test_wizard_has_nine_steps_and_catalogue_is_exposed(self):
        self.assertEqual(STEPS, 9)
        self.assertEqual(self.public.get("/api/setup/session").json()["steps"], 9)
        catalogue = self.public.get("/api/setup").json()["plan"]
        self.assertEqual(set(catalogue["purposes"]), set(purposes.PURPOSES))
        self.assertEqual(set(catalogue["consents"]), set(purposes.CONSENTS))

    def test_session_validates_new_fields(self):
        self.assertEqual(self.update(6, {"purposes": ["home", "work"]}).status_code, 200)
        self.assertEqual(self.update(6, {"purposes": ["bogus"]}).status_code, 400)
        self.assertEqual(self.update(7, {"consents": {"faces": "yes"}}).status_code, 400)
        self.assertEqual(self.update(7, {"consents": {"faces": False}, "skip": ["NUXIVA_FLEET"]}).status_code, 200)
        self.assertEqual(self.update(7, {"skip": ["NUXIVA_NOT_A_FEATURE"]}).status_code, 400)

    def test_plan_preview_does_not_apply_anything(self):
        with mock.patch.object(setup_api, "_apply") as apply:
            reply = self.public.post("/api/setup/plan", json={"purposes": ["home"], "consents": {"listening": True}}, headers=HEADERS)
        self.assertEqual(reply.status_code, 200)
        self.assertIn("ear", reply.json()["packages"])
        apply.assert_not_called()

    def finalize(self):
        from features.people import people
        with tempfile.TemporaryDirectory() as root, mock.patch.object(people, "PEOPLE_DIR", Path(root)), \
                mock.patch.object(learner_module.learner, "teach", return_value=True), \
                mock.patch.object(setup_api, "_apply") as apply:
            self.update(4, {"assistant_name": "Atlas", "owner_name": "Nunzio", "owner_last": "Tech", "packages": []})
            return self.public.post("/api/setup/finalize", json={}, headers=HEADERS), apply

    def test_finalize_refuses_while_consents_are_unanswered(self):
        self.update(6, {"purposes": ["security"]})
        reply, apply = self.finalize()
        self.assertEqual(reply.status_code, 409, reply.text)
        apply.assert_not_called()
        self.assertFalse(setup_api.done())

    def test_finalize_applies_the_plan_with_denied_packages_off(self):
        self.update(6, {"purposes": ["security"]})
        self.update(7, {"consents": {"cameras": True, "faces": False, "network_guard": True, "listening": True, "voiceprint": False}})
        reply, apply = self.finalize()
        self.assertEqual(reply.status_code, 200, reply.text)
        updates = apply.call_args.args[0]
        self.assertEqual(updates["NUXIVA_CAMERAS"], "1")
        self.assertEqual(updates["NUXIVA_VISION"], "0")
        self.assertEqual(updates["NUXIVA_EAR"], "1")
        self.assertEqual(updates["NUXIVA_NETGUARD"], "1")
        self.assertTrue(reply.json()["plan"]["purposes"] == ["security"])

    def test_finalize_without_purposes_keeps_the_old_behaviour(self):
        reply, apply = self.finalize()
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertNotIn("NUXIVA_CAMERAS", apply.call_args.args[0])
        self.assertIsNone(reply.json()["plan"])


if __name__ == "__main__":
    unittest.main()
