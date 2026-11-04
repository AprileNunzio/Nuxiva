import unittest
from backend.app_scanner import is_application, is_feature, scan_catalog


class AppScannerTest(unittest.TestCase):
    def test_apps_detection(self):
        self.assertTrue(is_application({"kind": "app"}))
        self.assertFalse(is_application({"kind": "feature"}))
        self.assertTrue(is_application({"id": "music"}))
        self.assertTrue(is_application({"id": "tv"}))
        self.assertFalse(is_application({"id": "bluetooth"}))

    def test_features_detection(self):
        self.assertTrue(is_feature({"kind": "feature"}))
        self.assertFalse(is_feature({"kind": "app"}))
        self.assertTrue(is_feature({"id": "bluetooth"}))
        self.assertFalse(is_feature({"id": "tv"}))

    def test_catalog_scan(self):
        catalog = scan_catalog()
        self.assertIn("apps", catalog)
        self.assertIn("features", catalog)
        app_ids = {a["id"] for a in catalog["apps"]}
        feature_ids = {f["id"] for f in catalog["features"]}
        self.assertIn("music", app_ids)
        self.assertIn("tv", app_ids)
        self.assertIn("bluetooth", feature_ids)


if __name__ == "__main__":
    unittest.main()
