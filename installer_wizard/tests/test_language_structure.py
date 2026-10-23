import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPES = (ROOT / "client_web/src/core_apps/people/language", ROOT / "installer_wizard/web/display/language",
          ROOT / "installer_wizard/widgets/chess_3d/language")
CODE = (ROOT / "client_web/src/core_apps/people/components", ROOT / "installer_wizard/web/display")
TRACKED = ("vitals_", "gg_", "tg_", "training_", "condition_", "open_control_panel")
KEY = re.compile(r"""\bt\(\s*['"]([a-z0-9_]+)['"]""")


class LanguageStructureTest(unittest.TestCase):
    def test_every_key_lives_inside_the_dictionary(self):
        for folder in SCOPES:
            for path in folder.glob("*.json"):
                with self.subTest(file=str(path.relative_to(ROOT))):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(set(data) - {"meta", "dictionary"}, set())

    def test_languages_have_the_same_keys(self):
        for folder in SCOPES:
            sets = {p.stem: {k for k in json.loads(p.read_text(encoding="utf-8"))["dictionary"] if folder != SCOPES[0] or k.startswith(TRACKED)}
                    for p in folder.glob("*.json")}
            base = sets["it"]
            for lang, keys in sets.items():
                with self.subTest(folder=folder.parent.name, lang=lang):
                    self.assertEqual(base ^ keys, set())

    def test_people_components_only_use_defined_keys(self):
        defined = set(json.loads((SCOPES[0] / "it.json").read_text(encoding="utf-8"))["dictionary"])
        missing = set()
        for path in CODE[0].glob("*.tsx"):
            for key in KEY.findall(path.read_text(encoding="utf-8")):
                if key not in defined:
                    missing.add((path.name, key))
        self.assertEqual(missing, set())
