import asyncio
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from features.update_center import guard, native
from features.update_center.progress import UpdateProgress


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


GOOD_SIG = "[GNUPG:] NEWSIG\n[GNUPG:] GOODSIG AB12 GitHub <noreply@github.com>\n[GNUPG:] VALIDSIG 9684 2024 0\n[GNUPG:] TRUST_FULLY 0 pgp\n"


class Engines:
    def engines(self):
        yield "python", False
        if native.RUST:
            yield "rust", True

    def run_both(self, fn):
        for name, rust in self.engines():
            with self.subTest(engine=name), mock.patch.object(native, "RUST", rust):
                fn()


class NativeBridgeTest(unittest.TestCase, Engines):
    def test_signature_verdicts(self):
        def check():
            self.assertEqual(native.signature(GOOD_SIG, 0)["verdict"], "trusted")
            bad = native.signature("[GNUPG:] BADSIG AB12 Mallory\n", 1)
            self.assertTrue(bad["blocking"])
            self.assertEqual(native.signature("[GNUPG:] GOODSIG AB12 X\n", 1)["verdict"], "bad")
            self.assertEqual(native.signature("[GNUPG:] ERRSIG AB12 1 8 00 1 9\n[GNUPG:] NO_PUBKEY AB12\n", 1)["verdict"], "unknown_key")
            self.assertEqual(native.signature("", 1), {"verdict": "unsigned", "blocking": False, "format": "none", "fingerprint": None, "signer": None})
            ssh = native.signature('Good "git" signature for dev@example.org with ED25519 key SHA256:abc\n', 0)
            self.assertEqual((ssh["verdict"], ssh["format"], ssh["fingerprint"]), ("valid", "ssh", "SHA256:abc"))
        self.run_both(check)

    def test_tree_verification_detects_tampering_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "ok.py").write_bytes(b"print(1)\n")
            (root / "src" / "evil.py").write_bytes(b"tampered\n")
            records = [
                f"100644 blob {blob(b'print(1)' + bytes([10]))}\tsrc/ok.py",
                f"100644 blob {blob(b'original' + bytes([10]))}\tsrc/evil.py",
                f"100644 blob {blob(b'x')}\tsrc/gone.py",
                f"100644 blob {blob(b'x')}\t../outside",
                f"160000 commit {blob(b'sub')}\tvendor/sub",
            ]
            raw = "\0".join(records) + "\0"

            def check():
                report = native.verify_tree(str(root), raw)
                self.assertEqual((report["checked"], report["matched"], report["skipped"]), (4, 1, 1))
                self.assertEqual(report["mismatched"], ["src/evil.py"])
                self.assertEqual(report["missing"], ["src/gone.py"])
                self.assertEqual(report["rejected"], ["../outside"])
                self.assertFalse(report["intact"])
                clean = native.verify_tree(str(root), records[0] + "\0")
                self.assertTrue(clean["intact"])
                self.assertEqual(len(clean["fingerprint"]), 64)
            self.run_both(check)

    def test_pipeline_is_forward_only(self):
        def check():
            state = native.pipeline_advance(None, "apply", "running", 1.0)
            self.assertEqual(state["stages"][0]["status"], "skipped")
            self.assertEqual(state["active"], "apply")
            with self.assertRaises(ValueError):
                native.pipeline_advance(state, "fetch", "running", 2.0)
            with self.assertRaises(ValueError):
                native.pipeline_advance(state, "apply", "bogus", 2.0)
            for stage, _ in native.STAGES:
                if stage != "apply" and state["stages"][[s for s, _ in native.STAGES].index(stage)]["status"] == "pending":
                    state = native.pipeline_advance(state, stage, "done", 3.0)
            state = native.pipeline_advance(state, "confirm", "done", 4.0) if not state["outcome"] else state
            self.assertEqual((state["percent"], state["outcome"]), (100, "success"))
        self.run_both(check)

    def test_rev_validation(self):
        def check():
            self.assertTrue(native.valid_rev("a" * 40))
            self.assertFalse(native.valid_rev("--upload-pack=x"))
            self.assertFalse(native.valid_rev("HEAD"))
        self.run_both(check)


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tracker = UpdateProgress(Path(self.tmp.name) / "progress.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bad_signature_stops_preflight(self):
        async def git(*args, timeout=0):
            return (1, "[GNUPG:] BADSIG AB12 Mallory\n") if args[0] == "verify-commit" else (0, "")
        self.tracker.begin("a" * 40, "b" * 40, "manuale")
        self.assertFalse(asyncio.run(guard.preflight(git, self.tracker, "a" * 40, "b" * 40, True)))
        run = self.tracker.run()
        self.assertEqual(run["pipeline"]["outcome"], "failed")
        self.assertEqual(run["signature"]["verdict"], "bad")

    def test_empty_tree_is_never_intact(self):
        async def git(*args, timeout=0):
            return 0, ""
        self.tracker.begin("a" * 40, "b" * 40, "manuale")
        self.tracker.step("apply", "done")
        self.assertFalse(asyncio.run(guard.postflight(git, self.tracker, Path(self.tmp.name), "b" * 40)))
        self.assertIn("empty_tree", self.tracker.run()["integrity"]["rejected"])

    def test_console_is_sanitized_and_persisted(self):
        self.tracker.log("check_done", "ok", "check", local="<script>abc", evil_key_that_is_far_too_long_for_rules=1)
        with self.assertRaises(ValueError):
            self.tracker.log("Bad Code")
        reloaded = UpdateProgress(self.tracker.path)
        line = reloaded.view()["console"][-1]
        self.assertEqual(line["args"], {"local": "scriptabc"})
        self.assertIsNone(reloaded.public())
        saved = json.loads(self.tracker.path.read_text())
        self.assertEqual(len(saved["console"]), 1)


if __name__ == "__main__":
    unittest.main()
