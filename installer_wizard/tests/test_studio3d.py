import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.models3d import generator, library, parts as ops, studio, voice

HAMMER = generator.TEMPLATES["martello"]


class PartsTests(unittest.TestCase):
    def test_clean_rejects_bad_input(self):
        with self.assertRaises(ops.PartError):
            ops.clean({"shape": "pyramid"})
        with self.assertRaises(ops.PartError):
            ops.clean({"shape": "box", "color": "red"})
        with self.assertRaises(ops.PartError):
            ops.clean({"shape": "box", "size": [1, 2]})
        with self.assertRaises(ops.PartError):
            ops.clean({"shape": "box", "position": [float("nan"), 0, 0]})

    def test_fresh_sits_on_the_ground_with_unique_name(self):
        parts = [ops.fresh([], "box", name="a")]
        second = ops.fresh(parts, "box", name="a")
        self.assertEqual(second["name"], "a 2")
        self.assertAlmostEqual(ops.bounds([second])["min"][1], 0.0, places=2)

    def test_set_dimension_is_exact_for_axis_aligned_parts(self):
        part = ops.fresh([], "box")
        ops.set_dimension(part, "y", 30)
        self.assertAlmostEqual(ops.extent(part)[1], 30.0, places=2)
        self.assertAlmostEqual(ops.extent(part)[0], 10.0, places=2)

    def test_find_by_words(self):
        parts = [ops.clean(p) for p in HAMMER]
        self.assertEqual(parts[ops.find(parts, "il manico")]["name"], "manico")
        self.assertEqual(parts[ops.find(parts, "la testa")]["name"], "testa")
        self.assertIsNone(ops.find(parts, "elicottero"))

    def test_ground_moves_lowest_point_to_zero(self):
        parts = [ops.fresh([], "box")]
        ops.translate(parts[0], "y", 7)
        ops.ground(parts)
        self.assertAlmostEqual(ops.bounds(parts)["min"][1], 0.0, places=2)


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(library, "ROOT", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)
        meta = library.create("Martello", "ai", {"parts": [ops.clean(p) for p in HAMMER], "how": "template"})
        self.meta = generator.render(meta)
        self.mid = self.meta["id"]
        studio.ACTIVE["id"] = None
        with mock.patch.object(studio.desk, "show"), mock.patch.object(studio.desk, "hide"):
            pass

    def test_edit_undo_redo_roundtrip(self):
        original = library.get(self.mid)["parts"]
        studio.operate(self.mid, {"op": "add", "shape": "sphere", "color": "#ff0000"})
        self.assertEqual(len(library.get(self.mid)["parts"]), len(original) + 1)
        studio.undo(self.mid)
        self.assertEqual(library.get(self.mid)["parts"], original)
        studio.redo(self.mid)
        self.assertEqual(len(library.get(self.mid)["parts"]), len(original) + 1)

    def test_files_are_rebuilt_after_edit(self):
        before = (library.folder(self.mid) / self.meta["main"]).read_bytes()
        studio.operate(self.mid, {"op": "scale", "index": 0, "factor": 2})
        self.assertNotEqual((library.folder(self.mid) / self.meta["main"]).read_bytes(), before)

    def test_invalid_operations_are_rejected(self):
        for body in ({"op": "remove", "index": 99}, {"op": "move", "index": 0, "axis": "w", "delta": 1},
                     {"op": "update", "index": 0, "changes": {"color": "nope"}}, {"op": "boom"}, {"op": "add", "shape": "cube"}):
            with self.assertRaises(studio.StudioError, msg=str(body)):
                studio.operate(self.mid, body)

    def test_voice_commands(self):
        studio.ACTIVE["id"] = self.mid
        with mock.patch.object(studio.desk, "show"), mock.patch.object(studio.desk, "hide"):
            reply, _ = voice.answer("sposta il manico a destra di 3 cm")
            self.assertIn("spostato", reply)
            self.assertAlmostEqual(library.get(self.mid)["parts"][0]["position"][0], 3.0)
            voice.answer("colora la testa di rosso")
            names = [p["name"] for p in library.get(self.mid)["parts"]]
            self.assertEqual(library.get(self.mid)["parts"][names.index("testa")]["color"], ops.COLORS["rosso"])
            voice.answer("aggiungi una sfera blu")
            self.assertEqual(library.get(self.mid)["parts"][-1]["shape"], "sphere")
            reply, _ = voice.answer("quanto è alto")
            self.assertIn("cm", reply)
            reply, _ = voice.answer("elimina il pezzo fantasma")
            self.assertIn("Non trovo", reply)
            reply, _ = voice.answer("annulla")
            self.assertEqual(reply, "Annullato.")
            with self.assertRaises(LookupError):
                voice.answer("che tempo fa domani")


if __name__ == "__main__":
    unittest.main()
