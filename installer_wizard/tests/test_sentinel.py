import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from agenti.sentinel import narrate, record, vault
from agenti.sentinel.collectors import automations
from agenti.sentinel.collectors.access import AccessCollector
from agenti.sentinel.collectors.presence import PresenceCollector
from agenti.sentinel.journal import Journal, SentinelUnavailable

ROOT = Path(__file__).resolve().parents[1]
LANG = ROOT / "agenti" / "sicurezza" / "sentinel" / "language"
T0 = 1_793_900_000.0


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustSentinel", None)


class Clock:
    def __init__(self, t: float = T0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class TempVault(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(vault, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)


class LanguageTests(unittest.TestCase):

    def test_every_narrative_exists_in_every_language(self):
        tables = {lang: json.loads((LANG / f"{lang}.json").read_text(encoding="utf-8")) for lang in narrate.LANGS}
        keys = set(tables["it"]["narrative"])
        for lang, data in tables.items():
            self.assertEqual(set(data["narrative"]), keys, lang)
            self.assertEqual(set(data["settings"]), set(tables["it"]["settings"]), lang)

    def test_sentences_are_composed_in_the_reader_language(self):
        event = {"narrative": {"key": "sentinel.presence.left_wearing", "params": {"person": "Nunzio", "color": "sentinel.color.grey"}}}
        self.assertEqual(narrate.text(event, "it"), "Ho visto Nunzio con un capo grigio andare via")
        self.assertEqual(narrate.text(event, "en"), "I saw Nunzio leave wearing something grey")
        self.assertEqual(narrate.text(event, "xx"), narrate.text(event, "it"))

    def test_params_cannot_inject_format_fields(self):
        event = {"narrative": {"key": "sentinel.presence.arrived", "params": {"person": "{person.__class__}"}}}
        self.assertEqual(narrate.text(event, "it"), "Ho visto {person.__class__} arrivare")
        self.assertEqual(narrate.text({"narrative": {"key": "sentinel.nope"}}, "it"), "")


class VaultTests(TempVault):

    def test_secrets_and_paths_are_private_and_validated(self):
        key = vault.secret("master")
        self.assertEqual(len(key), 32)
        self.assertEqual(stat.S_IMODE((self.root / "sentinel" / "master.key").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.root / "sentinel").stat().st_mode) & 0o077, 0)
        for bad in ("../x", "2026-1-1", "2026-11-05/../../etc"):
            with self.assertRaises(vault.VaultError):
                vault.day_path(bad)


class WithoutNativeTests(TempVault):

    def test_the_journal_refuses_without_the_engine(self):
        with mock.patch("agenti.sentinel.journal._engine_class", return_value=None):
            with self.assertRaises(SentinelUnavailable):
                Journal().ready()

    def test_recording_does_not_break_the_caller(self):
        with mock.patch("agenti.sentinel.journal._engine_class", return_value=None), \
                mock.patch.object(record, "journal", Journal()), mock.patch.object(record, "enabled", return_value=True):
            self.assertIsNone(record.record("presence.arrived", record.NUXIVA, "sentinel.presence.arrived"))


class CollectorTests(unittest.TestCase):

    def setUp(self):
        self.calls = []
        for target in ("agenti.sentinel.collectors.presence.record.record",
                       "agenti.sentinel.collectors.access.record.record",
                       "agenti.sentinel.collectors.automations.record.record"):
            patcher = mock.patch(target, side_effect=lambda kind, subject, key, params=None, *a, **k:
                                 self.calls.append((kind, key, params)))
            patcher.start()
            self.addCleanup(patcher.stop)
        for name in ("enabled", "option"):
            patcher = mock.patch.object(record, name, return_value=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(record, "pseudonym", side_effect=lambda slug: "ab" * 16)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("agenti.sentinel.collectors.presence.display_name", side_effect=str.title)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_arrivals_departures_guests_and_shutter(self):
        c = PresenceCollector()
        people = [{"known": True, "slug": "nunzio", "attire": {"color": "grey", "confidence": 0.8}}]
        c.update({"kind": "authorized", "members": [{"person": "nunzio"}], "guests": 0}, people, T0)
        c.update({"kind": "mixed", "members": [{"person": "nunzio"}], "guests": 2}, people, T0 + 5)
        c.update({"kind": "empty", "members": [], "guests": 0}, [], T0 + 9)
        kinds = [k for k, _, _ in self.calls]
        self.assertEqual(kinds, ["presence.arrived", "guest.arrived", "guest.arrived", "display.privacy_shutter",
                                 "presence.left", "guest.left", "guest.left"])
        self.assertEqual(self.calls[0][2], {"person": "Nunzio", "color": "sentinel.color.grey"})
        self.assertEqual([p["guest"] for k, _, p in self.calls if k == "guest.arrived"], [1, 2])

    def test_guest_numbers_restart_each_day(self):
        c = PresenceCollector()
        c.update({"kind": "guest_only", "members": [], "guests": 1}, [], T0)
        c.update({"kind": "empty", "members": [], "guests": 0}, [], T0 + 10)
        c.update({"kind": "guest_only", "members": [], "guests": 1}, [], T0 + 86_400 * 2)
        self.assertEqual([p["guest"] for k, _, p in self.calls if k == "guest.arrived"], [1, 1])

    def test_unknown_colours_are_never_reported(self):
        c = PresenceCollector()
        c.update({"kind": "authorized", "members": [{"person": "anna"}]}, [{"known": True, "slug": "anna", "attire": {"color": "<b>"}}], T0)
        self.assertEqual(self.calls[0][1], "sentinel.presence.arrived")

    def test_repeated_refusals_are_recorded_once_a_minute(self):
        c = AccessCollector()
        for _ in range(5):
            c.denied("", "guest", "tool", "ha_call_service", "guest")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2]["who"], "sentinel.word.guest")

    def test_automation_runs_are_recorded(self):
        automations.on_event({"name": "automation_started", "data": {"automation": "Controllo casa", "id": "a1"}})
        automations.on_event({"name": "automation_finished", "data": {"automation": "Controllo casa", "id": "a1", "status": "errore"}})
        automations.on_event({"name": "state_changed", "data": {}})
        self.assertEqual([k for k, _, _ in self.calls], ["automation.started", "automation.failed"])


class AppearanceTests(unittest.TestCase):

    def test_a_uniform_shirt_gives_its_colour_and_noise_gives_nothing(self):
        import sys
        sys.path.insert(0, str(ROOT / "agenti" / "percezione" / "vision"))
        import appearance
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (128, 128, 128)
        track = type("T", (), {"box": (280, 60, 80, 80), "frames": 0})()
        for n in range(8):
            track.frames = n * appearance.SAMPLE_EVERY
            appearance.observe(track, frame)
        self.assertEqual(appearance.view(track)["color"], "grey")
        noisy = np.random.default_rng(1).integers(0, 255, (480, 640, 3), dtype=np.uint8)
        other = type("T", (), {"box": (280, 60, 80, 80), "frames": 0})()
        for n in range(8):
            other.frames = n * appearance.SAMPLE_EVERY
            appearance.observe(other, noisy)
        self.assertIsNone(appearance.view(other))
        edge = type("T", (), {"box": (600, 400, 80, 80), "frames": 0})()
        appearance.observe(edge, frame)
        self.assertIsNone(appearance.dominant(frame, edge.box))


@unittest.skipUnless(_native(), "motore nativo non installato")
class NativeJournalTests(TempVault):

    def setUp(self):
        super().setUp()
        self.clock = Clock()
        self.journal = Journal(clock=self.clock)
        self.journal.swept_at = T0

    def event(self, n: int, kind: str = "presence.arrived", at: float = T0) -> dict:
        return {"id": f"{n:016x}", "at_ms": int((at + n) * 1000), "kind": kind,
                "subject": {"type": "person", "id": "ab" * 16}, "place": None,
                "narrative": {"key": "sentinel.presence.arrived", "params": {"person": "Nunzio"}},
                "sensitivity": "personal", "source": "presence", "links": []}

    def write(self, count: int):
        for n in range(count):
            self.journal.append(self.event(n))
        return self.journal.query({"from_ms": int(T0 * 1000) - 1000, "to_ms": int(T0 * 1000) + 86_400_000, "limit": 200})

    def test_events_are_encrypted_chained_and_signed(self):
        page = self.write(5)
        self.assertEqual(len(page["events"]), 5)
        day_file = next((self.root / "sentinel" / "days").glob("*.log"))
        self.assertNotIn(b"Nunzio", day_file.read_bytes())
        report = self.journal.integrity(day_file.stem)
        self.assertTrue(report["chain"] and report["signed"])

    def test_a_changed_byte_is_detected(self):
        self.write(3)
        day_file = next((self.root / "sentinel" / "days").glob("*.log"))
        data = bytearray(day_file.read_bytes())
        data[70] ^= 1
        day_file.write_bytes(bytes(data))
        fresh = Journal(clock=self.clock)
        with self.assertRaises(ValueError):
            fresh.query({"from_ms": int(T0 * 1000) - 1000, "to_ms": int(T0 * 1000) + 86_400_000, "limit": 200})

    def test_deleting_by_range_rechains_the_day(self):
        self.write(4)
        removed = self.journal.delete(int(T0 * 1000), int((T0 + 1.5) * 1000))
        self.assertEqual(removed, 2)
        day = next((self.root / "sentinel" / "days").glob("*.log")).stem
        self.assertTrue(self.journal.integrity(day)["signed"])

    def test_expired_days_are_erased_with_their_key(self):
        self.write(2)
        self.clock.t = T0 + 400 * 86_400
        result = self.journal.sweep()
        self.assertEqual(len(result["destroyed"]), 1)
        self.assertEqual(list((self.root / "sentinel" / "keys").glob("*.key")), [])

    def test_guest_appearance_is_trimmed_after_a_day(self):
        self.journal.append({**self.event(1, "guest.appearance"), "subject": {"type": "guest", "id": 1},
                             "narrative": {"key": "sentinel.guest.appearance", "params": {"guest": "1"}}})
        self.journal.append(self.event(2))
        self.clock.t = T0 + 2 * 86_400
        self.assertEqual(self.journal.sweep()["trimmed"], 1)

    def test_queries_are_bounded(self):
        with self.assertRaises(ValueError):
            self.journal.query({"from_ms": 0, "to_ms": 40 * 86_400_000, "limit": 10})


if __name__ == "__main__":
    unittest.main()
