import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_APPS_DIR = ROOT / "client_web" / "src" / "core_apps"


def discovered_apps():
    return sorted(path.parent for path in CORE_APPS_DIR.rglob("manifest.json"))


class CoreAppsIsolationAndSortingTests(unittest.TestCase):
    def test_all_discovered_core_apps_are_isolated(self):
        apps = discovered_apps()
        self.assertTrue(apps, "The scanner did not discover any applications")
        ids = set()
        for app_dir in apps:
            with self.subTest(app=app_dir.name):
                manifest = json.loads((app_dir / "manifest.json").read_text(encoding="utf-8"))
                self.assertNotIn(manifest["id"], ids)
                ids.add(manifest["id"])
                self.assertTrue((app_dir / "View.tsx").is_file())
                icon = (app_dir / manifest["icon3d"]).resolve()
                self.assertTrue(icon.is_relative_to(app_dir.resolve()), "The icon must belong to its app")
                self.assertTrue(icon.is_file())
                dictionaries = sorted((app_dir / "language").glob("*.json"))
                self.assertTrue(dictionaries, "Missing application-owned dictionaries")
                for dictionary in dictionaries:
                    data = json.loads(dictionary.read_text(encoding="utf-8"))
                    self.assertTrue(data["dictionary"]["title"].strip())
                    if "locale" in data.get("meta", {}):
                        self.assertEqual(data["meta"]["locale"], dictionary.stem)

    def test_dynamic_multilingual_alphabetical_sorting(self):
        """Every discovered locale covers every discovered app; no fixed totals or first title."""
        apps = discovered_apps()
        locales = sorted({path.stem for app in apps for path in (app / "language").glob("*.json")})
        self.assertTrue(locales)
        for locale in locales:
            with self.subTest(locale=locale):
                translated = {}
                for app_dir in apps:
                    language_file = app_dir / "language" / f"{locale}.json"
                    self.assertTrue(language_file.is_file(), f"Missing {locale} translation for {app_dir.name}")
                    data = json.loads(language_file.read_text(encoding="utf-8"))
                    translated[app_dir.name] = data["dictionary"]["title"]
                self.assertEqual(set(translated), {app.name for app in apps})
                ordered = sorted(translated, key=lambda app: translated[app].casefold())
                self.assertCountEqual(ordered, translated)
                for left, right in zip(ordered, ordered[1:]):
                    self.assertLessEqual(translated[left].casefold(), translated[right].casefold())


if __name__ == "__main__":
    unittest.main()
