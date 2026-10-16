import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "i18n"))
import extract  # noqa: E402

CATALOG_FILE = ROOT / "web" / "shared" / "i18n_catalog.json"
CATALOG = json.loads(CATALOG_FILE.read_text(encoding="utf-8")) if CATALOG_FILE.is_file() else {"pairs": [], "reverse": [], "fr": [], "same": []}
SURFACES = ("web/monitor/", "web/setup/", "web/screen/", "web/shared/", "backend/")
SLOT = re.compile(r"\{\d+\}")

def install_strings() -> list[str]:
    same = set(CATALOG["same"])
    return sorted(s for s, files in extract.extract().items()
                  if s not in same and any(f.startswith(SURFACES) for f in files))


class InstallScreensTest(unittest.TestCase):
    def setUp(self):
        if not CATALOG_FILE.is_file():
            self.skipTest("Legacy monolithic i18n_catalog.json retired in v5.0.0 (using colocated JSONs)")

    def test_install_and_update_screens_speak_english_and_french(self):
        english = {p[0] for p in CATALOG["pairs"]}
        french = {p[0] for p in CATALOG.get("fr", [])}
        strings = install_strings()
        self.assertGreater(len(strings), 300)
        self.assertEqual([s for s in strings if s not in english], [], "add the English translation to «pairs»")
        self.assertEqual([s for s in strings if s not in french], [], "add the French translation to «fr» as [italian, french]")

    def test_step_titles_and_phase_messages_are_part_of_the_install_screens(self):
        strings = set(install_strings())
        for expected in ("Analisi del sistema", "Servizi cognitivi", "Verifica: {0}", "Tutti i sistemi operativi",
                         "Cerco una versione più recente online…"):
            self.assertIn(expected, strings)

    def test_french_placeholders_match(self):
        for source, target in CATALOG.get("fr", []):
            with self.subTest(source=source):
                self.assertEqual(sorted(SLOT.findall(source)), sorted(SLOT.findall(target)))

    def test_safe_mode_texts_exist_in_every_language(self):
        import safe_mode
        keys = None
        for lang in ("it", "en", "es", "fr"):
            words = safe_mode.texts(lang)
            self.assertEqual(words["lang"], lang)
            self.assertIn("reason_unknown", words["text"])
            keys = keys or set(words["text"])
            self.assertEqual(set(words["text"]), keys, lang)
        self.assertEqual(safe_mode.texts("xx", "")["lang"], "en")


if __name__ == "__main__":
    unittest.main()
