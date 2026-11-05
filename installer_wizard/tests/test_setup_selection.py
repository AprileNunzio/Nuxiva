import unittest
from unittest import mock

import packages
import setup_api


class TestSetupSelection(unittest.TestCase):
    def setUp(self):
        from state import store
        self.saved_steps = {k: dict(v) for k, v in store.steps.items()}
        for sid in packages.PACKAGE_BY_STEP:
            store.steps.pop(sid, None)
        self.addCleanup(self._restore)

    def _restore(self):
        from state import store
        store.steps.clear()
        store.steps.update(self.saved_steps)

    def test_clean_returns_only_picked_packages(self):
        raw = {
            "name": "Nunzio",
            "lang": "it",
            "brain": "local",
            "packages": ["voice"],
        }
        cleaned = setup_api._clean(raw)
        self.assertEqual(cleaned.get("NUXIVA_VOICE_PACKAGE"), "1")
        self.assertNotIn("NUXIVA_VISION", cleaned)
        self.assertNotIn("NUXIVA_EAR", cleaned)
        self.assertEqual(cleaned.get("NUXIVA_LLM_MODEL"), "granite3.3:2b")

    def test_unpicked_packages_are_not_wanted_when_disabled(self):
        env = {
            "NUXIVA_VOICE_PACKAGE": "1",
            "NUXIVA_VISION": "0",
            "NUXIVA_EAR": "0",
        }
        with mock.patch("packages._detect", return_value=True):
            self.assertFalse(packages.wanted(packages.PACKAGE_BY_ID["vision"], env))
            self.assertFalse(packages.wanted(packages.PACKAGE_BY_ID["ear"], env))
            self.assertFalse(packages.step_wanted("vision", env))
            self.assertFalse(packages.step_wanted("ear", env))

    def test_soup_not_wanted_by_default(self):
        env = {"NUXIVA_BRAIN": "local"}
        self.assertFalse(packages.step_wanted("soup", env))

    def test_lightweight_model_profile_default(self):
        raw = {"brain": "local", "profile": "auto"}
        brain_out = setup_api._brain(raw)
        self.assertEqual(brain_out["NUXIVA_LLM_MODEL"], "granite3.3:2b")


if __name__ == "__main__":
    unittest.main()
