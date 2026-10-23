import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from feature_localization import localize_feature


def manifest(feature: str) -> dict:
    data = json.loads((ROOT / "features" / feature / "feature.json").read_text(encoding="utf-8"))
    return {**data, "dir": str(ROOT / "features" / feature), "source": "system"}


class GuideTest(unittest.TestCase):
    def test_telegram_and_google_have_guides_in_every_language(self):
        for feature in ("telegram", "google"):
            for lang in ("it", "en", "fr", "es"):
                guide = localize_feature(manifest(feature), lang)["guide"]
                self.assertTrue(guide and len(guide["steps"]) >= 5, (feature, lang))
                self.assertTrue(all(link["url"].startswith("https://") for link in guide["links"]))

    def test_every_setting_has_help_text(self):
        for feature in ("telegram", "google"):
            settings = localize_feature(manifest(feature), "it")["settings"]
            secrets = [s for s in settings if s["type"] in ("secret", "text") and s["key"].startswith(("NUXIVA_TELEGRAM", "NUXIVA_GOOGLE_CLIENT"))]
            self.assertTrue(all(s.get("help") for s in secrets), feature)

    def test_unsafe_links_and_bad_shapes_are_dropped(self):
        from feature_localization import _guide
        out = _guide({"steps": ["a", 3], "links": [{"label": "x", "url": "javascript:alert(1)"}, {"label": "ok", "url": "https://t.me/BotFather"}, "x"]})
        self.assertEqual(out["steps"], ["a"])
        self.assertEqual([link["url"] for link in out["links"]], ["https://t.me/BotFather"])
        self.assertIsNone(_guide({"steps": [], "links": []}))
        self.assertIsNone(_guide("x"))


if __name__ == "__main__":
    unittest.main()
