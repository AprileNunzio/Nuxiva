import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center import native, notes
from agenti.update_center.progress import UpdateProgress

REPO = Path(__file__).resolve().parents[2]


def text(word: str) -> dict:
    return {"it": f"{word} it", "en": f"{word} en", "fr": f"{word} fr", "es": f"{word} es"}


def note(date: str = "2026-11-13", features=None, fixes=None, **extra) -> str:
    body = {"schema": 1, "date": date, "title": text("Titolo"),
            "features": [text("Nuovo")] if features is None else features,
            "fixes": [] if fixes is None else fixes, **extra}
    return json.dumps(body, ensure_ascii=False)


NAME = "20261113060000-prova.json"

CASES = [
    (NAME, note()),
    ("20261112000000-vecchia.json", note("2026-11-12", features=[], fixes=[text("Fix")])),
    ("../fuga.json", note()),
    ("20261113060000-Maiuscole.json", note()),
    ("20261114000000-data.json", note()),
    (NAME, note(features=[], fixes=[])),
    (NAME, note(features=[{**text("x"), "it": "a‮b"}])),
    (NAME, note(features=[{**text("x"), "it": "a\u0007b"}])),
    (NAME, note(features=[{**text("x"), "it": "   "}])),
    (NAME, note(features=[{**text("x"), "it": "x" * 321}])),
    (NAME, note(features=[text("x")] * 25)),
    (NAME, note(html="<script>")),
    (NAME, note(schema=2)),
    (NAME, note(schema=True)),
    (NAME, note(features=[{"it": "solo italiano"}])),
    (NAME, '{"schema":1,"schema":1}'),
    (NAME, "non json"),
    (NAME, " " * (notes.MAX_FILE_BYTES + 1)),
    (NAME, note(title={**text("t"), "en": "t" * 141})),
]


class Engines:
    def engines(self):
        yield "python", False
        if native.RUST and hasattr(native._native, "update_release_notes"):
            yield "rust", True

    def run_both(self, fn):
        for name, rust in self.engines():
            with self.subTest(engine=name), mock.patch.object(native, "RUST", rust):
                fn()


class ParseTest(unittest.TestCase, Engines):
    def test_valid_note_is_sanitized_and_sorted(self):
        def check():
            out = notes.digest([("20261112000000-vecchia.json", note("2026-11-12")), (NAME, note())])
            self.assertEqual([n["id"] for n in out["notes"]], ["20261113060000-prova", "20261112000000-vecchia"])
            self.assertEqual(out["features"], 2)
            self.assertEqual(out["rejected"], [])
        self.run_both(check)

    def test_hostile_notes_rejected(self):
        expected = ["name", "name", "date", "empty", "text", "text", "text", "text", "too_many", "malformed",
                    "schema", "malformed", "malformed", "malformed", "malformed", "too_large", "text"]

        def check():
            out = notes.digest(CASES[2:])
            self.assertEqual(out["notes"], [])
            self.assertEqual([r["reason"] for r in out["rejected"]], expected)
            self.assertEqual(out["rejected"][0]["file"], "")
        self.run_both(check)

    def test_rust_python_parity(self):
        if not (native.RUST and hasattr(native._native, "update_release_notes")):
            self.skipTest("nuxiva_native senza update_release_notes")
        rust = json.loads(native._native.update_release_notes(json.dumps(CASES)))
        self.assertEqual(rust, notes.py_digest(CASES))

    def test_repository_notes_are_valid(self):
        files = [(p.name, p.read_text(encoding="utf-8")) for p in (REPO / notes.DIR).glob("*.json")]
        self.assertTrue(files)
        self.assertEqual(notes.py_digest(files)["rejected"], [])

    def test_added_files_filters_paths(self):
        raw = "\0".join(["changelog/20261113060000-a.json", "changelog/sub/20261113060000-b.json",
                         "changelog/README.md", "server/x.json", "changelog/../x.json", ""])
        self.assertEqual(notes.added_files(raw), ["20261113060000-a.json"])

    def test_compact_limits_items(self):
        report = notes.py_digest([(NAME, note(features=[text(str(i)) for i in range(20)]))])
        view = notes.compact(report, limit=5)
        self.assertEqual(len(view["features"]), 5)
        self.assertEqual(view["total_features"], 20)
        self.assertIsNone(notes.compact(notes.empty()))

    def test_compact_exposes_date_and_safe_version(self):
        report = notes.py_digest([(NAME, note(features=[text("a")]))])
        self.assertEqual(notes.compact(report)["date"], "2026-11-13")
        self.assertIsNone(notes.compact(report)["version"])
        self.assertEqual(notes.compact({**report, "version": "5.9.0"})["version"], "5.9.0")
        self.assertIsNone(notes.compact({**report, "version": "<script>"})["version"])


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cmd("init", "-q", "-b", "main")
        self.cmd("config", "user.email", "ci@example.invalid")
        self.cmd("config", "user.name", "ci")
        (self.root / "README").write_text("x")
        self.cmd("add", ".")
        self.cmd("commit", "-q", "-m", "base")
        self.base = self.cmd("rev-parse", "HEAD")
        (self.root / notes.DIR).mkdir()
        (self.root / notes.DIR / NAME).write_text(note(fixes=[text("Fix")]), encoding="utf-8")
        (self.root / notes.DIR / "20261113060000-rotta.json").write_text("{", encoding="utf-8")
        self.cmd("add", ".")
        self.cmd("commit", "-q", "-m", "feat: note")
        self.target = self.cmd("rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True,
                              text=True).stdout.strip()

    async def git(self, *args: str, timeout: float = 0):
        proc = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        return proc.returncode, (proc.stdout + proc.stderr).strip()

    def test_collects_only_added_notes_between_revisions(self):
        out = asyncio.run(notes.collect(self.git, self.base, self.target))
        self.assertEqual([n["id"] for n in out["notes"]], ["20261113060000-prova"])
        self.assertEqual(out["fixes"], 1)
        self.assertEqual(out["rejected"], [{"file": "20261113060000-rotta.json", "reason": "malformed"}])
        same = asyncio.run(notes.collect(self.git, self.target, self.target))
        self.assertEqual(same["notes"], [])

    def test_rejects_invalid_revisions(self):
        out = asyncio.run(notes.collect(self.git, "HEAD~1", "--output=/tmp/x"))
        self.assertEqual(out, notes.empty())

    def test_progress_exposes_compact_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UpdateProgress(Path(tmp) / "p.json")
            tracker.begin(self.base, self.target, "manuale")
            tracker.attach("notes", asyncio.run(notes.collect(self.git, self.base, self.target)))
            tracker.step("check", "done")
            view = tracker.public()
            self.assertEqual(view["notes"]["fixes"][0]["it"], "Fix it")
            self.assertEqual(UpdateProgress(Path(tmp) / "p.json").public()["notes"], view["notes"])


if __name__ == "__main__":
    unittest.main()
