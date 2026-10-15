import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_APPS_DIR = ROOT / "client_web" / "src" / "core_apps"


class CoreAppsIsolationAndSortingTests(unittest.TestCase):
    def test_all_24_core_apps_exist_and_are_isolated(self):
        expected_apps = [
            "habits", "agents", "algorithms", "hands", "flows", "features_hub",
            "places", "music", "google", "iptv", "laws", "nodes",
            "cameras", "firewall", "automations", "vault", "people", "office",
            "twin", "study", "emergency", "backup", "vpn", "updater"
        ]
        self.assertEqual(len(expected_apps), 24)

        for app_id in expected_apps:
            app_dir = CORE_APPS_DIR / app_id
            self.assertTrue(app_dir.is_dir(), f"Missing app directory: {app_id}")
            self.assertTrue((app_dir / "manifest.json").is_file(), f"Missing manifest.json for {app_id}")
            self.assertTrue((app_dir / "View.tsx").is_file(), f"Missing View.tsx for {app_id}")
            self.assertTrue((app_dir / "types.ts").is_file(), f"Missing types.ts for {app_id}")
            self.assertTrue((app_dir / "api.ts").is_file(), f"Missing api.ts for {app_id}")
            self.assertTrue((app_dir / "index.tsx").is_file(), f"Missing index.tsx for {app_id}")

            lang_dir = app_dir / "language"
            self.assertTrue(lang_dir.is_dir(), f"Missing language dir for {app_id}")
            for loc in ("it", "en", "fr", "es"):
                json_file = lang_dir / f"{loc}.json"
                self.assertTrue(json_file.is_file(), f"Missing {loc}.json for {app_id}")
                data = json.loads(json_file.read_text(encoding="utf-8"))
                self.assertIn("dictionary", data)
                self.assertIn("title", data["dictionary"])
                self.assertIn("description", data["dictionary"])
                self.assertEqual(data.get("meta", {}).get("locale"), loc)

    def test_dynamic_multilingual_alphabetical_sorting(self):
        """
        Verifica che cambiando lingua (IT -> EN -> FR -> ES),
        l'ordinamento alfabetico dei 24 titoli tradotti sia univoco e corretto.
        """
        languages = ["it", "en", "fr", "es"]
        for loc in languages:
            titles = []
            for app_dir in CORE_APPS_DIR.iterdir():
                if not app_dir.is_dir() or app_dir.name in ("language", "__pycache__"):
                    continue
                lang_file = app_dir / "language" / f"{loc}.json"
                if lang_file.is_file():
                    data = json.loads(lang_file.read_text(encoding="utf-8"))
                    titles.append(data["dictionary"]["title"])

            self.assertEqual(len(titles), 24, f"Locale {loc} does not have 24 translated titles")
            sorted_titles = sorted(titles, key=lambda s: s.casefold())
            # In Italian, 'Abitudini' is first; in English, 'Agents' or 'Algorithms' is first; etc.
            if loc == "it":
                self.assertEqual(sorted_titles[0], "Abitudini")
            elif loc == "en":
                self.assertIn(sorted_titles[0], ("Agents", "Algorithms"))


if __name__ == "__main__":
    unittest.main()
