import tempfile
import unittest
from pathlib import Path

from features.desktop.desk import Desk
from features.desktop.novelty import AUTO_CAP, MAX_PENALTY, Novelty


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.day = "2026-10-22"


class NoveltyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = Clock()
        self.path = Path(self.temp.name) / "n.json"

    def make(self):
        return Novelty(self.path, lambda: self.clock.day, lambda: self.clock.now)

    def test_penalty_grows_with_time_seen_and_is_capped(self):
        novelty = self.make()
        self.assertEqual(novelty.penalty("meteo"), 0.0)
        novelty.tick([("meteo", "a", False)], 300)
        self.assertAlmostEqual(novelty.penalty("meteo"), 20.0)
        novelty.tick([("meteo", "a", False)], 6000)
        self.assertEqual(novelty.penalty("meteo"), MAX_PENALTY)

    def test_new_information_resets_the_penalty(self):
        novelty = self.make()
        novelty.tick([("meteo", "a", False)], 600)
        novelty.tick([("meteo", "b", False)], 1)
        self.assertLess(novelty.penalty("meteo"), 1.0)

    def test_cyclic_widgets_are_not_reset_by_data_changes(self):
        novelty = self.make()
        novelty.tick([("clock", "a", True)], 600)
        novelty.tick([("clock", "b", True)], 1)
        self.assertGreater(novelty.penalty("clock"), 30.0)

    def test_a_new_day_forgets_everything(self):
        novelty = self.make()
        novelty.tick([("meteo", "a", False)], 600)
        self.clock.day = "2026-10-23"
        self.assertEqual(novelty.penalty("meteo"), 0.0)

    def test_exposure_survives_a_restart_on_the_same_day_only(self):
        novelty = self.make()
        novelty.tick([("meteo", "a", False)], 300)
        novelty.save()
        self.assertGreater(self.make().penalty("meteo"), 0.0)
        self.clock.day = "2026-10-23"
        self.assertEqual(self.make().penalty("meteo"), 0.0)

    def test_corrupt_file_starts_fresh(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.make().penalty("meteo"), 0.0)


class RotationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.desk = Desk.__new__(Desk)
        self.desk.novelty = Novelty(Path(self.temp.name) / "n.json")

    def item(self, wid, priority, **extra):
        return {"id": wid, "key": f"bind:{wid}", "priority": priority, "shown_at": 1.0, **extra}

    def test_seen_widgets_make_room_for_unseen_ones(self):
        items = [self.item(f"w{i}", 60 - i) for i in range(AUTO_CAP + 2)]
        self.desk.novelty.tick([("w0", "x", False), ("w1", "x", False)], 600)
        shown = [i["id"] for i in self.desk._rotate(items)]
        self.assertEqual(len(shown), AUTO_CAP)
        self.assertNotIn("w0", shown)
        self.assertIn("w5", shown)

    def test_forced_widgets_are_never_dropped_or_penalised(self):
        items = [self.item("urgente", 10, urgent=True), self.item("ora", 20, essential=True),
                 self.item("ricordo", 5, key="recall:x")]
        items += [self.item(f"w{i}", 50) for i in range(AUTO_CAP + 3)]
        self.desk.novelty.tick([("urgente", "x", False)], 6000)
        shown = [i["id"] for i in self.desk._rotate(items)]
        self.assertEqual(shown[:3].count("urgente") + shown[:3].count("ora") + shown[:3].count("ricordo"), 3)
        self.assertEqual(len(shown), 3 + AUTO_CAP)


if __name__ == "__main__":
    unittest.main()
