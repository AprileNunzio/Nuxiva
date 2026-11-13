import json
import unittest
from pathlib import Path

from agenti.team import observability
from tests.test_context_hot import HotContextBase, NATIVE

WIDGET = Path(__file__).resolve().parents[1] / "agenti" / "cognizione" / "team" / "widget" / "team_health"
LANGS = ("it", "en", "fr", "es")
SECRETS = ("Anna", "Rossi", "funghi", "jazz", "Vegetariana", "ingegnera", "Luca", "Ospite", "senza zucchero", "1990")


def _numbers_and_tokens(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from _numbers_and_tokens(v)
    elif isinstance(value, list):
        for v in value:
            yield from _numbers_and_tokens(v)
    else:
        yield str(value)


class SnapshotShapeTest(unittest.TestCase):
    def test_snapshot_is_a_closed_set_of_counters_and_flags(self):
        snap = observability.snapshot()
        self.assertEqual(set(snap), {"squad", "engine", "memory", "alerts"})
        for section in ("squad", "memory"):
            self.assertTrue(all(isinstance(v, (int, bool)) for v in snap[section].values()))
        self.assertIn(snap["engine"]["mode"], ("python", "shadow", "rust"))
        self.assertTrue(set(snap["alerts"]) <= {"engine_unavailable", "decision_drift", "engine_errors", "memory_cold"})


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class SnapshotPrivacyTest(HotContextBase):
    def test_no_personal_content_in_metrics(self):
        self.family()
        hot_text = self.hot_context()
        self.assertIn("Anna", hot_text)
        snap = observability.snapshot()
        self.assertTrue(snap["memory"]["loaded"])
        self.assertGreaterEqual(snap["memory"]["persons"], 3)
        dumped = json.dumps(snap, ensure_ascii=False)
        for secret in SECRETS:
            self.assertNotIn(secret, dumped)
        for token in _numbers_and_tokens(snap):
            self.assertLess(len(token), 40)

    def hot_context(self):
        from agenti.people import hot
        return hot.context_for(["anna"])


class WidgetLanguageTest(unittest.TestCase):
    def test_four_languages_have_identical_keys(self):
        keys = {}
        for lang in LANGS:
            doc = json.loads((WIDGET / "language" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["meta"]["locale"], lang)
            keys[lang] = set(doc["dictionary"])
        self.assertEqual(len({frozenset(k) for k in keys.values()}), 1)

    def test_every_translated_key_is_used_and_every_used_key_exists(self):
        source = (WIDGET / "widget.js").read_text(encoding="utf-8")
        dictionary = set(json.loads((WIDGET / "language" / "it.json").read_text(encoding="utf-8"))["dictionary"])
        for key in ("label", "agents", "busy", "people", "attention", "say_fine", "say_attention"):
            self.assertIn(f'"{key}"', source)
            self.assertIn(key, dictionary)
        for alert in ("engine_unavailable", "decision_drift", "engine_errors", "memory_cold"):
            self.assertIn(f"alert_{alert}", dictionary)

    def test_widget_manifest_has_no_background_or_border_chrome(self):
        manifest = json.loads((WIDGET / "widget.json").read_text(encoding="utf-8"))
        self.assertIs(manifest["chrome"], False)
        self.assertEqual(manifest["id"], "team_health")
