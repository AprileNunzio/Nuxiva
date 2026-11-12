import json
import re
import unittest
from pathlib import Path

from features.desktop.desk import desk
from features.desktop.manifest import REFRESH_MAX, REFRESH_MIN, clamp_refresh

WIDGETS = Path(__file__).resolve().parent.parent / "widgets"
LANGS = ("it", "en", "es", "fr")
LITERAL = re.compile(r'(?<![\w.])(?:ctx\.)?t\(\s*"([a-z0-9_.]+)"')
TERNARY = re.compile(r'(?<![\w.])(?:ctx\.)?t\(([^()`]*\?[^()`]*)\)')
QUOTED = re.compile(r'"([a-z0-9_.]+)"')
COMMON = re.compile(r'\btc\(\s*"([a-z0-9_.]+)"')
COUNT = re.compile(r'\bcount\(\s*"([a-z0-9_.]+)"')
DYNAMIC = re.compile(r'(?<![\w.])(?:ctx\.)?t\(\s*`([a-z0-9_.]*)\$\{')


def dictionary(scope, lang):
    return json.loads((WIDGETS / scope / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]


def widget_dirs():
    return sorted(p for p in WIDGETS.iterdir() if (p / "widget.json").exists())


class WidgetLanguageTest(unittest.TestCase):
    def test_all_languages_share_the_same_keys(self):
        for scope in [p.name for p in widget_dirs() if (p / "language").exists()] + ["common"]:
            reference = set(dictionary(scope, "it"))
            for lang in LANGS:
                self.assertEqual(set(dictionary(scope, lang)), reference, f"{scope}/{lang}")
                for key, value in dictionary(scope, lang).items():
                    self.assertTrue(value.strip(), f"{scope}/{lang}/{key}")

    def test_used_keys_exist(self):
        common = set(dictionary("common", "it"))
        for folder in widget_dirs():
            source = (folder / "widget.js").read_text(encoding="utf-8")
            keys = set(LITERAL.findall(source))
            for expr in TERNARY.findall(source):
                keys.update(QUOTED.findall(expr.split("?", 1)[1]))
            for base in COUNT.findall(source):
                keys.update({f"{base}_one", f"{base}_other"})
            prefixes = DYNAMIC.findall(source)
            if not keys and not prefixes:
                continue
            for lang in LANGS:
                available = set(dictionary(folder.name, lang))
                self.assertFalse(keys - available, f"{folder.name}/{lang}: {sorted(keys - available)}")
                for prefix in prefixes:
                    self.assertTrue(any(k.startswith(prefix) for k in available), f"{folder.name}/{lang}: {prefix}")
            for key in COMMON.findall(source):
                self.assertIn(key, common, f"{folder.name}: {key}")

    def test_no_demo_data_in_manifests(self):
        for folder in widget_dirs():
            manifest = json.loads((folder / "widget.json").read_text(encoding="utf-8"))
            self.assertNotIn("demo", manifest, folder.name)

    def test_refresh_is_clamped(self):
        self.assertIsNone(clamp_refresh(0))
        self.assertEqual(clamp_refresh(-5), REFRESH_MIN)
        self.assertEqual(clamp_refresh(10**9), REFRESH_MAX)
        self.assertEqual(clamp_refresh(30), 30)

    def test_desk_publishes_refresh(self):
        desk.scan()
        for item in desk.active():
            self.assertIn("refresh", item)


if __name__ == "__main__":
    unittest.main()
