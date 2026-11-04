import json
import tempfile
import unittest
from pathlib import Path

from features.desktop import manifest
from features.desktop.desk import Desk


def widget(root: Path, wid: str, **extra) -> None:
    folder = root / wid
    folder.mkdir()
    (folder / "widget.js").write_text("NuxivaDesk.register('x', {render() {}});", encoding="utf-8")
    (folder / "widget.json").write_text(json.dumps({"id": wid, "name": wid, "intents": [wid], **extra}), encoding="utf-8")


class StickyTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        widget(self.root, "partita", sticky=True, immersive=True, size="full", priority=95, essential=True)
        widget(self.root, "meteo")
        widget(self.root, "lavagna", standalone=True, size="full")
        from features.desktop import desk as desk_module
        from unittest import mock
        for patch in (mock.patch.object(desk_module, "SYSTEM_DIR", self.root), mock.patch.object(desk_module, "USER_DIR", self.root / "none"),
                      mock.patch.object(desk_module, "STATE_FILE", self.root / "state.json"), mock.patch.object(desk_module, "NOVELTY_FILE", self.root / "nov.json")):
            patch.start()
            self.addCleanup(patch.stop)
        self.desk = Desk()
        self.desk.scan()

    def test_manifest_flags_are_read(self):
        self.assertTrue(self.desk.widgets["partita"]["sticky"])
        self.assertTrue(self.desk.widgets["partita"]["immersive"])
        self.assertFalse(self.desk.widgets["meteo"]["sticky"])

    def test_standalone_content_survives_matching_intent_and_idle(self):
        content = {"strokes": [{"points": [[1, 2], [3, 4]]}], "board_id": "board-1"}
        self.desk.show("lavagna", content, fullscreen=True)
        self.desk.on_intent("lavagna", {})
        self.assertEqual(self.desk.instances["lavagna"]["data"], content)
        self.assertFalse(self.desk.instances["lavagna"]["intent"])
        self.desk.went_idle()
        self.desk.on_intent("meteo", {"title": "Weather"})
        self.assertEqual(self.desk.instances["lavagna"]["data"], content)
        self.assertTrue(self.desk.instances["lavagna"]["fullscreen"])
        self.assertTrue(self.desk.instances["meteo"]["intent"])
        self.desk.went_idle()
        self.assertNotIn("meteo", self.desk.instances)
        self.assertTrue(self.desk.dismiss("lavagna"))
        self.assertNotIn("lavagna", self.desk.instances)

    def test_intent_does_not_implicitly_open_standalone_widget(self):
        self.desk.on_intent("lavagna", {})
        self.assertNotIn("lavagna", self.desk.instances)

    def test_sticky_widget_survives_idle_and_other_requests(self):
        self.desk.show("partita", {}, key="partita", intent=True, fullscreen=True)
        self.desk.show("meteo", {}, key="meteo", intent=True)
        self.desk.went_idle()
        self.assertIn("partita", self.desk.instances)
        self.assertNotIn("meteo", self.desk.instances)
        self.desk.on_intent("meteo", {})
        self.assertIn("partita", self.desk.instances)
        self.desk.dismiss_intents()
        self.assertIn("partita", self.desk.instances)

    def test_sticky_widget_still_closes_when_asked(self):
        self.desk.show("partita", {}, key="partita", intent=True)
        self.desk.hide(key="partita")
        self.assertNotIn("partita", self.desk.instances)
        self.desk.show("partita", {}, key="partita", intent=True)
        self.assertTrue(self.desk.dismiss("partita"))
        self.assertNotIn("partita", self.desk.instances)

    def test_active_exposes_immersive_state_to_the_display(self):
        self.desk.show("partita", {}, key="partita", fullscreen=True)
        item = next(i for i in self.desk.active() if i["key"] == "partita")
        self.assertTrue(item["immersive"])
        self.assertTrue(item["sticky"])
        self.assertTrue(item["fullscreen"])

    def test_normalize_is_strict_about_flags(self):
        data = {"id": "a", "name": "a", "sticky": "yes", "immersive": 1, "refresh": "abc", "size": "huge", "tone": "pink"}
        folder = self.root / "partita"
        manifest.normalize(data, folder, self.root)
        self.assertFalse(data["sticky"])
        self.assertFalse(data["immersive"])
        self.assertIsNone(data["refresh"])
        self.assertEqual((data["size"], data["tone"]), ("m", "cyan"))

    def test_the_chess_board_is_sticky_and_immersive(self):
        real = json.loads((Path(__file__).resolve().parents[1] / "widgets" / "chess_3d" / "widget.json").read_text(encoding="utf-8"))
        self.assertTrue(real["sticky"] and real["immersive"] and real["chrome"] is False)


if __name__ == "__main__":
    unittest.main()
