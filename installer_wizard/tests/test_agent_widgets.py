import json
import unittest
from pathlib import Path

from agenti._registry import registry
from agenti._widgets import WIDGET_DIR, MANIFEST
from config import WIDGETS_DIR


class AgentWidgetsTest(unittest.TestCase):
    def test_shared_folder_holds_only_the_common_words(self):
        entries = sorted(p.name for p in Path(WIDGETS_DIR).iterdir())
        self.assertEqual(entries, ["common"])

    def test_every_agent_declares_exactly_the_widgets_it_ships(self):
        for agent in registry.agents():
            base = agent.dir / WIDGET_DIR
            shipped = sorted(p.name for p in base.iterdir() if (p / MANIFEST).is_file()) if base.is_dir() else []
            declared = json.loads((agent.dir / "feature.json").read_text(encoding="utf-8")).get("widgets", [])
            with self.subTest(agent=agent.id):
                self.assertEqual(sorted(declared), shipped)

    def test_widget_ids_are_unique_across_agents(self):
        seen = {}
        for agent in registry.agents():
            base = agent.dir / WIDGET_DIR
            if not base.is_dir():
                continue
            for p in base.iterdir():
                if (p / MANIFEST).is_file():
                    self.assertNotIn(p.name, seen, f"{p.name} in {agent.id} and {seen.get(p.name)}")
                    seen[p.name] = agent.id


class WidgetManifestFieldsTest(unittest.TestCase):
    def manifests(self):
        for agent in registry.agents():
            base = agent.dir / WIDGET_DIR
            if base.is_dir():
                for p in sorted(base.iterdir()):
                    if (p / MANIFEST).is_file():
                        yield p.name, json.loads((p / MANIFEST).read_text(encoding="utf-8"))

    def test_every_widget_declares_category_and_is_frameless(self):
        from agenti.desktop.manifest import CATEGORIES, MEDIA
        seen = 0
        for wid, data in self.manifests():
            with self.subTest(widget=wid):
                self.assertIn(data.get("category"), CATEGORIES)
                self.assertIs(data.get("chrome"), False)
                self.assertIn(data.get("media"), (None, *MEDIA))
                self.assertIn(data.get("exclusive"), (None, *MEDIA))
            seen += 1
        self.assertGreater(seen, 50)

    def test_planner_candidate_reads_manifest_fields(self):
        from agenti.desktop import planner_bridge
        item = {"id": "tv_player", "key": "k", "category": "media", "media": "audio", "exclusive": "video", "size": "full"}
        got = planner_bridge.candidate(item, 1000.0)
        self.assertEqual((got["category"], got["media"], got["exclusive"]), ("media", "audio", "video"))
        small = planner_bridge.candidate({**item, "size": "m", "category": "bogus"}, 1000.0)
        self.assertIsNone(small["exclusive"])
        self.assertIsNone(small["category"])


class NoOrphanWidgetsTest(unittest.TestCase):
    def test_every_widget_folder_belongs_to_a_registered_agent(self):
        from config import AGENTS_DIR
        disk = {p.parent.name for p in Path(AGENTS_DIR).glob("*/*/widget/*/widget.json")}
        owned = set()
        for agent in registry.agents():
            base = agent.dir / WIDGET_DIR
            if base.is_dir():
                owned |= {p.name for p in base.iterdir() if (p / MANIFEST).is_file()}
        self.assertEqual(disk - owned, set())
