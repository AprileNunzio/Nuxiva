import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenti import _widget_check
from agenti._registry import SYSTEM_DIR

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "widget_inspect")


def shipped():
    return sorted(p.parent for p in SYSTEM_DIR.glob("*/*/widget/*/widget.json"))


def build(root: Path, mode: str, script: str, title: str = "Titolo", say: str = "Tutto bene") -> Path:
    (root / "language").mkdir(parents=True, exist_ok=True)
    (root / "widget.json").write_text(json.dumps({"id": "demo", "category": "home", "chrome": False,
                                                  "simple": {"icon": "home", "mode": mode}}), encoding="utf-8")
    (root / "widget.js").write_text(script, encoding="utf-8")
    for lang in ("it", "en", "fr", "es"):
        (root / "language" / f"{lang}.json").write_text(
            json.dumps({"meta": {}, "dictionary": {"simple_title": title, "say_ok": say}}), encoding="utf-8")
    return root


class WidgetCheckTest(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)

    def codes(self, folder: Path) -> list[str]:
        return [f"{i['field']}:{i['code']}" for i in _widget_check.inspect(folder)]

    def test_every_shipped_widget_is_clean(self):
        folders = shipped()
        self.assertGreater(len(folders), 50)
        for folder in folders:
            with self.subTest(widget=folder.name):
                self.assertEqual(self.codes(folder), [])

    def test_collapsible_needs_a_headline(self):
        folder = build(self.temp / "a", "collapse", "x = {};")
        self.assertEqual(self.codes(folder), ["widget.js:headline.missing"])
        folder = build(self.temp / "b", "collapse", "x = { headline() {} };")
        self.assertEqual(self.codes(folder), [])

    def test_language_defects(self):
        folder = build(self.temp / "c", "open", "x = {};", title="  ")
        self.assertIn("language/it.json:simple_title.invalid", self.codes(folder))
        folder = build(self.temp / "d", "open", "x = {};", say="y" * 120)
        self.assertIn("language/fr.json:say.invalid", self.codes(folder))
        (folder / "language" / "en.json").unlink()
        self.assertIn("language/en.json:unreadable", self.codes(folder))

    def test_manifest_rules(self):
        bad = {"id": "Bad Id", "category": "nope", "chrome": True, "media": "smell", "simple": {"icon": "A B", "mode": "zoom"}}
        got = [f"{i['field']}:{i['code']}" for i in _widget_check.check_manifest(bad)]
        for want in ("id:invalid", "category:invalid", "chrome:must_be_false", "media:invalid", "simple.icon:invalid", "simple.mode:invalid"):
            self.assertIn(want, got)
        self.assertEqual(sum(1 for i in _widget_check.check_manifest({"id": "ok"}) if i["field"] == "simple"), 1)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class WidgetCheckParityTest(unittest.TestCase):
    def test_native_matches_python_on_shipped_and_broken_trees(self):
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, True)
        broken = [build(temp / "ok", "collapse", "x = { headline() {} };"),
                  build(temp / "nohead", "collapse", "x = {};"),
                  build(temp / "title", "open", "x = {};", title=""),
                  build(temp / "say", "open", "x = {};", say="z" * 200),
                  temp / "missing"]
        (broken[0] / "language" / "es.json").unlink()
        for folder in [*shipped(), *broken]:
            with self.subTest(folder=folder.name):
                self.assertEqual(json.loads(nuxiva_native.widget_inspect(str(folder))), _widget_check.inspect(folder))


if __name__ == "__main__":
    unittest.main()
