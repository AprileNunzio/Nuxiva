import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "client_web" / "src" / "core_apps"
LANGS = ("it", "en", "es", "fr")
CALL = re.compile(r"""\bt\(\s*['"]([a-z0-9_]+)['"]""")
PARAM = re.compile(r"\{(\w+)\}")


def dictionary(app: Path, lang: str) -> dict:
    rows = json.loads((app / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
    return {k: v for k, v in rows.items() if not (app.name == "people" and k.startswith("field_"))}


class CoreAppsLanguageTests(unittest.TestCase):
    def apps(self):
        return sorted(p for p in ROOT.iterdir() if (p / "language").is_dir())

    def test_every_language_has_the_same_keys(self):
        for app in self.apps():
            reference = set(dictionary(app, "it"))
            for lang in LANGS:
                self.assertEqual(reference, set(dictionary(app, lang)), f"{app.name}/{lang}")

    def test_no_empty_translation(self):
        for app in self.apps():
            for lang in LANGS:
                for key, value in dictionary(app, lang).items():
                    self.assertTrue(str(value).strip(), f"{app.name}/{lang}/{key}")

    def test_placeholders_match_across_languages(self):
        for app in self.apps():
            base = dictionary(app, "it")
            for lang in LANGS[1:]:
                other = dictionary(app, lang)
                for key, value in base.items():
                    self.assertEqual(set(PARAM.findall(value)), set(PARAM.findall(other[key])), f"{app.name}/{lang}/{key}")

    def test_keys_used_by_the_code_exist(self):
        shared = {k for app in self.apps() for k in dictionary(app, "it")}
        for app in self.apps():
            known = set(dictionary(app, "it"))
            scope = f"useScopedI18n('core_apps/{app.name}')"
            sources = [f for f in app.rglob("*.tsx") if scope in f.read_text(encoding="utf-8")]
            for source in sources:
                for key in CALL.findall(source.read_text(encoding="utf-8")):
                    if key in shared and key not in known:
                        self.fail(f"{source.relative_to(ROOT)} usa «{key}» assente in {app.name}")
