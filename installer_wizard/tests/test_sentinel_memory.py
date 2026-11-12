import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.sentinel import memory_people, memory_vault, record, vault
from agenti.sentinel.journal import SentinelUnavailable
from agenti.sentinel.memory import Memory, new_id

T0 = 1_793_900_000.0
OWNER = "0123456789abcdef0123456789abcdef"


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustMemory", None)


def sighting(who: dict, at: float, upper: str = "red", items=("parcel",), hi_vis: bool = False) -> dict:
    return {"id": new_id(), "start_ms": int(at * 1000), "end_ms": int(at * 1000) + 20_000, "camera": "ingresso",
            "zone": "porta", "class": "person", "who": who,
            "look": {"upper": upper, "lower": "blue", "carrying": list(items), "hi_vis": hi_vis, "height_cm": 176},
            "gait": [0.25] * 16, "evidence": [{"kind": "frame", "id": "abcdef0123456789", "at_ms": int(at * 1000)}],
            "confidence": 0.8}


class Clock:
    def __init__(self, t: float = T0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


@unittest.skipIf(_native() is None, "nuxiva_native.RustMemory not built")
class MemoryTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(vault, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clock = Clock()
        self.memory = Memory(clock=self.clock)
        self.memory.swept_at = T0

    def _fill(self):
        unknown = {"type": "unknown"}
        owner = {"type": "person", "id": OWNER}
        guest = {"type": "guest", "id": 4}
        self.memory.add(sighting(unknown, T0 - 3600, hi_vis=True))
        self.memory.add(sighting(owner, T0 - 1800, upper="green", items=()))
        self.memory.add(sighting(guest, T0 - 900))
        return unknown, owner, guest

    def test_files_are_encrypted_and_private(self):
        self._fill()
        day = memory_vault.days()[0]
        data = memory_vault.read_day(day)
        self.assertNotIn(b"ingresso", data)
        self.assertNotIn(b"parcel", data)
        self.assertEqual(memory_vault.day_path(day).stat().st_mode & 0o077, 0)

    def test_search_by_look_returns_newest_first(self):
        self._fill()
        page = self.memory.search({"from_ms": int((T0 - 7200) * 1000), "to_ms": int(T0 * 1000), "upper": "red",
                                   "items": ["parcel"], "limit": 10})
        self.assertEqual(len(page["sightings"]), 2)
        self.assertEqual(page["sightings"][0]["who"], {"type": "guest", "id": 4})
        self.assertEqual(page["opened"], 2)

    def test_courier_query_by_hi_vis(self):
        self._fill()
        page = self.memory.search({"from_ms": int((T0 - 7200) * 1000), "to_ms": int(T0 * 1000), "hi_vis": True,
                                   "classes": ["person"]})
        self.assertEqual([s["who"]["type"] for s in page["sightings"]], ["unknown"])

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.memory.add({**sighting({"type": "unknown"}, T0), "camera": "../etc"})
        with self.assertRaises(ValueError):
            self.memory.add({**sighting({"type": "unknown"}, T0), "plate": "AB123CD"})
        with self.assertRaises(ValueError):
            self.memory.search({"from_ms": 10, "to_ms": 1})

    def test_forget_and_relink(self):
        _, owner, guest = self._fill()
        self.assertEqual(self.memory.forget(owner), 1)
        self.assertEqual(self.memory.profile(owner)["count"], 0)
        target = {"type": "person", "id": "fedcba9876543210fedcba9876543210"}
        self.assertEqual(self.memory.relink(guest, target), 1)
        profile = self.memory.profile(target)
        self.assertEqual(profile["count"], 1)
        self.assertEqual(profile["upper"][0], ["red", 1])

    def test_strangers_expire_before_household(self):
        self._fill()
        self.clock.t = T0 + 2 * 86400
        result = self.memory.sweep()
        self.assertEqual(result["trimmed"], 2)
        day = memory_vault.days()[0]
        left = json.loads(self.memory.ready().open(memory_vault.wrapped_key(day, None), day, memory_vault.read_day(day)))
        self.assertEqual([s["who"]["type"] for s in left], ["person"])

    def test_pinned_sighting_survives(self):
        unknown, _, _ = self._fill()
        page = self.memory.search({"from_ms": int((T0 - 7200) * 1000), "to_ms": int(T0 * 1000), "who": unknown})
        target = page["sightings"][0]
        day = memory_vault.days()[0]
        self.assertTrue(self.memory.pin(day, target["id"], True))
        self.clock.t = T0 + 3 * 86400
        self.memory.sweep()
        left = self.memory.search({"from_ms": int((T0 - 7200) * 1000), "to_ms": int(T0 * 1000), "who": unknown})
        self.assertEqual([s["id"] for s in left["sightings"]], [target["id"]])

    def test_policy_limits(self):
        with self.assertRaises(ValueError):
            self.memory.configure({"passerby": 30})
        self.assertEqual(self.memory.configure({"passerby": 7})["passerby"], 7)
        self.assertEqual(memory_vault.load_policy(), {"passerby": 7})


class IdentityTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(vault, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_unnamed_guest_profile_maps_to_guest(self):
        self.assertEqual(memory_people.who_for("ospite-7", {"slug": "ospite-7", "name": "Ospite 7"}),
                         {"type": "guest", "id": 7})

    def test_named_profile_maps_to_pseudonym(self):
        who = memory_people.who_for("nunzio", {"slug": "nunzio", "name": "Nunzio"})
        self.assertEqual(who, {"type": "person", "id": record.pseudonym("nunzio")})
        self.assertNotIn("nunzio", json.dumps(who))

    def test_missing_profile(self):
        with mock.patch.object(memory_people, "_profile", return_value=None):
            self.assertIsNone(memory_people.who_for("nessuno"))

    def test_consent_blocks_details(self):
        self.assertFalse(memory_people.allows_details({"consent": False}))

    def test_forget_without_engine_is_quiet(self):
        with mock.patch.object(memory_people.memory, "forget", side_effect=SentinelUnavailable("x")):
            self.assertEqual(memory_people.forget("nunzio", {"slug": "nunzio", "name": "Nunzio"}), 0)


if __name__ == "__main__":
    unittest.main()
