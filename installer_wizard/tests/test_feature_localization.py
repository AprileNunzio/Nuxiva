import json
import tempfile
import unittest
from pathlib import Path

from feature_localization import localize_feature


class FeatureLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder / "language").mkdir()
        for language, name in [("en", "Diagnostics"), ("it", "Diagnostica")]:
            data = {"name": name, "description": name + " description", "settings": {"MODE": name + " mode"}}
            (self.folder / "language" / (language + ".json")).write_text(json.dumps({"dictionary": data}), encoding="utf-8")
        self.manifest = {"dir": str(self.folder), "name": "Original", "settings": [{"key": "MODE", "label": "Original mode", "value": "auto"}]}

    def tearDown(self):
        self.temp.cleanup()

    def test_own_dictionary_labels_are_used_without_mutating_values_or_source(self):
        result = localize_feature(self.manifest, "it")
        self.assertEqual(result["name"], "Diagnostica")
        self.assertEqual(result["settings"][0]["label"], "Diagnostica mode")
        self.assertEqual(result["settings"][0]["value"], "auto")
        self.assertEqual(self.manifest["name"], "Original")
        self.assertEqual(self.manifest["settings"][0]["label"], "Original mode")

    def test_region_and_scanned_fallback_are_supported_without_path_traversal(self):
        self.assertEqual(localize_feature(self.manifest, "it-IT")["name"], "Diagnostica")
        self.assertEqual(localize_feature(self.manifest, "zz")["name"], "Diagnostics")
        self.assertIs(localize_feature(self.manifest, "../../secrets"), self.manifest)
