import unittest
from unittest import mock

import packages
import setup_api


class TestSetupSelection(unittest.TestCase):
    def test_clean_sets_zero_for_unpicked_packages(self):
        raw = {
            "name": "Nunzio",
            "lang": "it",
            "brain": "local",
            "packages": ["voice"],
        }
        cleaned = setup_api._clean(raw)
        self.assertEqual(cleaned.get("NUXIVA_VOICE_PACKAGE"), "1")
        self.assertEqual(cleaned.get("NUXIVA_VISION"), "0")
        self.assertEqual(cleaned.get("NUXIVA_EAR"), "0")
        self.assertEqual(cleaned.get("NUXIVA_DOCUMENTS"), "0")
        self.assertEqual(cleaned.get("NUXIVA_LLM_MODEL"), "granite3.3:2b")

    def test_unpicked_packages_are_not_wanted(self):
        raw = {
            "name": "Nunzio",
            "lang": "it",
            "brain": "local",
            "packages": ["display"],
        }
        cleaned = setup_api._clean(raw)
        with mock.patch("packages._detect", return_value=True):
            self.assertFalse(packages.wanted(packages.PACKAGE_BY_ID["vision"], cleaned))
            self.assertFalse(packages.wanted(packages.PACKAGE_BY_ID["ear"], cleaned))
            self.assertFalse(packages.step_wanted("vision", cleaned))
            self.assertFalse(packages.step_wanted("ear", cleaned))

    def test_soup_not_wanted_by_default(self):
        env = {"NUXIVA_BRAIN": "local"}
        self.assertFalse(packages.step_wanted("soup", env))

    def test_lightweight_model_profile_default(self):
        raw = {"brain": "local", "profile": "auto"}
        brain_out = setup_api._brain(raw)
        self.assertEqual(brain_out["NUXIVA_LLM_MODEL"], "granite3.3:2b")


if __name__ == "__main__":
    unittest.main()
