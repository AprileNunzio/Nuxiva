import asyncio
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
if str(EAR) not in sys.path:
    sys.path.append(str(EAR))

import feedback
import journal as journal_module
import livecap
import livegov

RATE = 16000


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class GovernorTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.load = {"value": 0.1}
        self.gov = livegov.LiveGovernor(self.clock, lambda: self.load["value"])
        patch = mock.patch.dict("os.environ", {}, clear=False)
        patch.start()
        self.addCleanup(patch.stop)

    def test_auto_allows_when_calm(self):
        self.assertTrue(self.gov.allowed())

    def test_high_load_suspends_then_resumes_with_backoff(self):
        self.load["value"] = 1.4
        self.assertFalse(self.gov.allowed())
        self.load["value"] = 0.1
        self.clock.now += 5
        self.assertFalse(self.gov.allowed())
        self.clock.now += livegov.PAUSE_FIRST
        self.assertTrue(self.gov.allowed())
        self.load["value"] = 1.4
        self.clock.now += 10
        self.assertFalse(self.gov.allowed())
        self.assertGreater(self.gov.paused_until - self.clock.now, livegov.PAUSE_FIRST)

    def test_slow_decoding_suspends(self):
        for _ in range(4):
            self.gov.record(2.0)
        self.assertFalse(self.gov.allowed())
        self.assertEqual(self.gov.reason, "slow")

    def test_interval_follows_decode_time(self):
        self.gov.record(0.1)
        self.assertEqual(self.gov.interval(), livegov.MIN_INTERVAL)
        self.gov.decode = 0.6
        self.assertAlmostEqual(self.gov.interval(), 1.32, places=2)

    def test_modes(self):
        with mock.patch.dict("os.environ", {"NUXIVA_EAR_LIVE": "off"}):
            self.assertFalse(self.gov.allowed())
            self.assertFalse(self.gov.status()["active"])
        with mock.patch.dict("os.environ", {"NUXIVA_EAR_LIVE": "on"}):
            self.load["value"] = 5.0
            self.assertTrue(self.gov.allowed())
            self.gov.record(5.0)
            self.assertTrue(self.gov.allowed())

    def test_background_work_waits_for_a_calm_machine(self):
        self.load["value"] = 2.0
        self.assertFalse(self.gov.background_ok())


class StabilityTest(unittest.TestCase):
    def test_common_prefix_ignores_case_and_punctuation(self):
        self.assertEqual(livecap.stable_count(["Accendi", "la", "luce,"], ["accendi", "la", "luce", "della"]), 3)
        self.assertEqual(livecap.stable_count(["a", "b"], ["x", "b"]), 0)
        self.assertEqual(livecap.stable_count([], ["a"]), 0)


class CaptionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events = []
        self.texts = ["accendi", "accendi la luce"]
        self.gov = livegov.LiveGovernor(time.monotonic, lambda: 0.0)

        async def send(**event):
            self.events.append(event)

        def decode(audio, lang):
            return self.texts.pop(0) if self.texts else "accendi la luce"

        self.caps = livecap.LiveCaptions(send, self.gov, decode, lambda audio: ("anna", 0.8, True), asyncio.Lock())
        self.frames = [np.zeros(int(RATE * 1.6), dtype=np.float32)]

    async def settle(self):
        for task in (self.caps.task, self.caps.speaker_task):
            if task is not None:
                await task

    async def test_partials_are_sequenced_and_stabilised(self):
        utt = self.caps.begin(True)
        self.caps.next_at = 0.0
        self.caps.tick(self.frames, "it", True)
        await self.settle()
        self.caps.next_at = 0.0
        self.caps.tick(self.frames, "it", True)
        await self.settle()
        partials = [e for e in self.events if e["type"] == "partial"]
        self.assertEqual([p["seq"] for p in partials], [1, 2])
        self.assertEqual(partials[1]["stable"], 1)
        self.assertTrue(all(p["utt"] == utt for p in partials))
        self.assertEqual(partials[-1]["speaker"], "anna")

    async def test_end_returns_last_text_and_resets(self):
        self.caps.begin(False)
        self.caps.next_at = 0.0
        self.caps.tick(self.frames, "it", False)
        await self.settle()
        result = self.caps.end()
        self.assertEqual(result["text"], "accendi")
        self.assertTrue(result["live"])
        self.assertEqual(self.caps.utt, "")

    async def test_too_little_audio_is_ignored(self):
        self.caps.begin(True)
        self.caps.next_at = 0.0
        self.caps.tick([np.zeros(1000, dtype=np.float32)], "it", True)
        self.assertIsNone(self.caps.task)

    async def test_nothing_while_the_model_is_busy_or_governor_denies(self):
        self.caps.begin(True)
        self.caps.next_at = 0.0
        await self.caps.lock.acquire()
        self.caps.tick(self.frames, "it", True)
        self.assertIsNone(self.caps.task)
        self.caps.lock.release()
        with mock.patch.dict("os.environ", {"NUXIVA_EAR_LIVE": "off"}):
            self.caps.tick(self.frames, "it", True)
        self.assertIsNone(self.caps.task)


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = journal_module.Journal(Path(self.tmp.name) / "j")
        self.audio = (np.sin(np.linspace(0, 200, RATE)) * 0.3).astype(np.float32)

    def test_text_is_encrypted_at_rest(self):
        self.log.record("command", "accendi la luce del salotto", "it", "anna", 0.8, True, 120, True, self.audio)
        raw = (Path(self.tmp.name) / "j" / "journal.db").read_bytes()
        self.assertNotIn(b"salotto", raw)
        clip = next((Path(self.tmp.name) / "j").glob("*.clip")).read_bytes()
        self.assertNotIn(b"RIFF", clip)

    def test_record_list_and_filters(self):
        self.log.record("command", "accendi la luce", "it", "anna", 0.8, True, 100, True, self.audio)
        self.log.record("heard", "che bella giornata", "it", None, 0.1)
        self.assertEqual(len(self.log.entries()), 2)
        self.assertEqual([e["text"] for e in self.log.entries(kind="heard")], ["che bella giornata"])
        self.assertEqual([e["speaker"] for e in self.log.entries(speaker="anna")], ["anna"])
        self.assertEqual(len(self.log.entries(speaker="-")), 1)
        self.assertEqual(len(self.log.entries(query="BELLA")), 1)
        self.assertEqual(self.log.record("heard", "   "), "")
        self.assertEqual(self.log.record("boh", "testo"), "")

    def test_audio_roundtrip(self):
        entry = self.log.record("command", "ciao", audio=self.audio)
        restored = journal_module.samples(self.log.audio(entry))
        self.assertEqual(len(restored), len(self.audio))
        self.assertIsNone(self.log.audio("0" * 12))
        self.assertIsNone(self.log.audio("../etc/passwd"))

    def test_feedback_lifecycle(self):
        entry = self.log.record("heard", "ehi nuxiba accendi", "it")
        self.assertTrue(self.log.feedback(entry, "wrong", "ehi nuxiva accendi", "Anna ", "note"))
        self.assertTrue(self.log.feedback(entry, "wrong", "ehi nuxiva accendi", "anna", "note"))
        row = self.log.get(entry)
        self.assertEqual((row["verdict"], row["correction"], row["fix_speaker"], row["note"]),
                         ("wrong", "ehi nuxiva accendi", "anna", "note"))
        self.assertEqual([e["id"] for e in self.log.pending()], [entry])
        self.log.mark_applied(entry)
        self.assertEqual(self.log.pending(), [])
        self.assertFalse(self.log.feedback(entry, "boh"))
        self.assertFalse(self.log.feedback("zz", "ok"))
        self.assertEqual(self.log.stats()["wrong"], 1)

    def test_prune_keeps_unapplied_feedback_and_drops_old_audio(self):
        old = self.log.record("heard", "vecchio", audio=self.audio)
        kept = self.log.record("heard", "da rivedere", audio=self.audio)
        fresh = self.log.record("heard", "recente", audio=self.audio)
        self.log.feedback(kept, "wrong", "da rivedere bene")
        import sqlite3
        with sqlite3.connect(self.log.db_path) as conn:
            conn.execute("UPDATE entries SET ts = ? WHERE id IN (?, ?)", (time.time() - 40 * 86400, old, kept))
        self.assertEqual(self.log.prune(14, 3, 300), 1)
        self.assertIsNone(self.log.get(old))
        self.assertIsNotNone(self.log.get(kept))
        self.assertTrue(self.log.get(kept)["audio"])
        self.assertTrue(self.log.get(fresh)["audio"])
        self.assertEqual(self.log.prune(14, 0, 300), 0)
        self.assertFalse(self.log.get(fresh)["audio"])

    def test_delete_and_purge(self):
        first = self.log.record("heard", "uno", audio=self.audio)
        self.log.record("heard", "due", audio=self.audio)
        self.assertTrue(self.log.delete(first))
        self.assertFalse(self.log.delete(first))
        self.assertEqual(self.log.purge(), 1)
        self.assertEqual(list((Path(self.tmp.name) / "j").glob("*.clip")), [])


class MissingCryptographyTest(unittest.TestCase):
    def test_the_listener_survives_without_the_cipher_library(self):
        import capture
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = journal_module.Journal(Path(tmp.name) / "j")
        with mock.patch.dict(sys.modules, {"cryptography": None, "cryptography.fernet": None}):
            with self.assertRaises(journal_module.JournalUnavailable):
                log.record("heard", "ciao")
        capture.BROKEN["reason"] = ""
        with mock.patch.object(capture.journal, "record", side_effect=journal_module.JournalUnavailable("mancante")):
            asyncio.run(capture.store(print, "heard", "ciao", "it", None, 0.0, False, 0, {"live": False}, None))
        self.assertEqual(capture.BROKEN["reason"], "mancante")
        self.assertFalse(capture.journal_on())
        capture.BROKEN["reason"] = ""


class FeedbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = journal_module.Journal(Path(self.tmp.name) / "j")
        self.audio = (np.sin(np.linspace(0, 200, RATE * 2)) * 0.3).astype(np.float32)
        self.prints = mock.Mock(ready=True)
        self.prints.embed.return_value = np.ones(4, dtype=np.float32)
        self.prints.add.return_value = 3

    def test_wrong_speaker_trains_the_right_voice(self):
        entry = self.log.record("heard", "frase", "it", "marco", audio=self.audio)
        self.log.feedback(entry, "wrong", "", "anna")
        self.assertEqual(feedback.apply_pending(self.prints, self.log), 1)
        self.prints.add.assert_called_once()
        self.assertEqual(self.prints.add.call_args.args[0], "anna")
        self.assertEqual(self.prints.add.call_args.args[2], "feedback")
        self.assertEqual(self.log.pending(), [])

    def test_missed_name_is_taught(self):
        entry = self.log.record("heard", "ehi nuxiba accendi la luce", "it")
        self.log.feedback(entry, "wrong", "ehi nuxiva accendi la luce")
        with mock.patch.object(feedback.learner, "find_wake", side_effect=lambda t: (0, 4, "nuxiva") if "nuxiva" in t else None), \
                mock.patch.object(feedback, "name_variant", return_value="nuxiba"), \
                mock.patch.object(feedback.learner, "teach", return_value=True) as teach:
            feedback.apply_pending(self.prints, self.log)
        teach.assert_called_once_with("nuxiba")

    def test_confirmed_entries_change_nothing(self):
        entry = self.log.record("command", "accendi", "it", "anna", audio=self.audio)
        self.log.feedback(entry, "ok")
        feedback.apply_pending(self.prints, self.log)
        self.prints.add.assert_not_called()
        self.assertEqual(self.log.pending(), [])


if __name__ == "__main__":
    unittest.main()
