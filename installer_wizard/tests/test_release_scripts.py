import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "release"))

import plan
import release_notes

TEXT = {"it": "a", "en": "b", "fr": "c", "es": "d"}


class PlanTest(unittest.TestCase):
    def tags(self, *names):
        return sorted((plan.key(plan.TAG.fullmatch(n).group(1)), plan.TAG.fullmatch(n).group(1), n) for n in names)

    def test_next_version_is_above_every_tag_and_the_version_file(self):
        tags = self.tags("assistant-v5.8.3", "android-v5.8.4", "v5.8.2")
        self.assertEqual(plan.next_version(tags, "5.8.3", "patch"), "5.8.5")
        self.assertEqual(plan.next_version(tags, "5.9.0", "patch"), "5.9.1")
        self.assertEqual(plan.next_version([], "5.8.3", "minor"), "5.9.0")

    def test_unified_tags_are_the_baseline_when_present(self):
        tags = self.tags("assistant-v5.8.9", "v5.8.4")
        self.assertEqual(plan.previous_tag(tags), "v5.8.4")
        self.assertEqual(plan.previous_tag(self.tags("assistant-v5.8.3", "android-v5.8.4")), "android-v5.8.4")

    def test_foreign_tags_are_ignored(self):
        self.assertIsNone(plan.TAG.fullmatch("other-v1.0.0"))


class NotesTest(unittest.TestCase):
    def notes(self):
        item = {"it": "x", "en": "x", "fr": "x", "es": "x"}
        return [{"id": "n1", "date": "2026-11-15", "title": TEXT, "features": [item], "fixes": [item]},
                {"id": "n2", "date": "2026-11-15", "title": TEXT, "features": [item, TEXT], "fixes": []}]

    def test_duplicates_are_merged_and_sources_are_kept(self):
        features = release_notes.flatten(self.notes(), "features")
        self.assertEqual([f["source"] for f in features], ["n1", "n2"])

    def test_release_document_is_complete_and_the_body_has_all_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk, exe = Path(tmp, "Nuxiva.apk"), Path(tmp, "Nuxiva_Setup.exe")
            apk.write_bytes(b"a" * 10)
            exe.write_bytes(b"b" * 20)
            release = release_notes.build("5.8.4", "v5.8.4", "f" * 40, "", [apk, exe], self.notes())
        self.assertEqual({a["platform"] for a in release["assets"]}, {"android", "windows"})
        self.assertEqual(release["summary"], {"notes": 2, "features": 2, "fixes": 1})
        body = release_notes.body(release, "AprileNunzio/Nuxiva")
        for heading in ("Novità", "New features", "Nouveautés", "Novedades"):
            self.assertIn(heading, body)
        self.assertIn("releases/download/v5.8.4/Nuxiva.apk", body)
        json.dumps(release)

    def test_components_are_aligned_in_the_repository(self):
        release = release_notes.build("5.8.4", "v5.8.4", "f" * 40, "", [], [])
        self.assertEqual({c["version"] for c in release["components"].values()}, {release["components"]["server"]["version"]})


if __name__ == "__main__":
    unittest.main()
