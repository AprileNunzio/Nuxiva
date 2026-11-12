import json
import unittest

from config import WIDGETS_DIR
from agenti import _layout, _widgets
from agenti._registry import registry
from agenti.medico.algorithms.reading import may_read, summary
from agenti.medico.vitals.model import METRICS


class MedicoAgentTest(unittest.TestCase):
    def test_medico_is_a_complete_health_agent(self):
        agent = registry.get("medico")
        self.assertEqual(agent.category, "salute")
        self.assertTrue(_layout.inspect(agent.dir)["complete"])
        self.assertEqual(registry.search("quanti battiti ha il cuore")[0][0], "medico")
        names = {json.loads((agent.dir / "language" / f"{lang}.json").read_text(encoding="utf-8"))["name"]
                 for lang in _layout.LANGUAGES}
        self.assertEqual(len(names), 4)

    def test_people_no_longer_owns_vitals(self):
        people = registry.get("people").dir
        self.assertFalse((people / "vitals").exists())
        self.assertFalse((people / "wellbeing").exists())

    def test_health_data_needs_consent(self):
        self.assertTrue(may_read({"slug": "a"}))
        self.assertFalse(may_read({"consent": False}))
        self.assertFalse(may_read({"share_health": False}))
        self.assertFalse(may_read({"role": "guest"}))
        self.assertTrue(may_read({"role": "guest", "share_health": True}))
        self.assertFalse(may_read(None))

    def test_summary_keeps_only_known_metrics_with_units(self):
        view = {"values": {"heart_rate": {"value": 71.6, "kind": "watch"}, "body_temp": {"value": "36.66", "kind": "x"},
                           "unknown": {"value": 1}, "hrv": {"value": "n/a"}},
                "recovery": {"score": 64, "band": "mid", "from": ["hrv"]},
                "signals": [{"metric": "heart_rate", "code": "high", "level": "watch", "extra": 1}], "sources": ["watch"]}
        out = summary(view, METRICS)
        self.assertEqual(out["values"]["heart_rate"], {"value": 72, "unit": "bpm", "source": "watch"})
        self.assertEqual(out["values"]["body_temp"]["value"], 36.7)
        self.assertNotIn("unknown", out["values"])
        self.assertNotIn("hrv", out["values"])
        self.assertEqual(out["recovery"], {"score": 64, "band": "mid"})
        self.assertEqual(out["signals"], [{"metric": "heart_rate", "code": "high", "level": "watch"}])
        self.assertEqual(summary({}, METRICS), {"available": False})

    def test_tool_is_private_and_owned_by_medico(self):
        from agenti.agent import registry as tools
        from agenti.medico.tools import medico_tools
        row = tools.TOOLS["medico_parametri"]
        self.assertTrue(row["full_only"])
        self.assertEqual(row["agent"], "medico")
        self.assertIs(row["fn"], medico_tools.medico_parametri)


class AgentWidgetsTest(unittest.TestCase):
    def test_widgets_live_with_their_agent(self):
        owners = {p.parent.name: owner for p, owner in _widgets.manifests(WIDGETS_DIR)}
        self.assertEqual(owners["vital_check"], "medico")
        self.assertEqual(owners["chess_3d"], "games")
        self.assertEqual(owners["clock"], "")
        self.assertFalse((WIDGETS_DIR / "vital_check").exists())

    def test_widget_ids_are_unique_across_agents_and_shared_folder(self):
        ids = [p.parent.name for p, _ in _widgets.manifests(WIDGETS_DIR)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_desk_and_team_find_agent_widgets(self):
        from agenti.desktop.desk import Desk
        from agenti.team.scanner import AgentScanner
        desk = Desk()
        desk.scan()
        self.assertEqual(desk.widgets["vital_check"]["source"], "system")
        self.assertTrue(desk.widgets["vital_check"]["dir"].endswith("salute/medico/widget/vital_check"))
        widgets = AgentScanner()._scan_widgets([str(p) for p, _ in _widgets.manifests(WIDGETS_DIR)])
        self.assertIn("vital_check", widgets)

    def test_widget_texts_resolve_from_the_agent_folder(self):
        from agenti.locale.colocated.api import roots
        bases = roots.roots["widgets"]
        self.assertIn(WIDGETS_DIR, bases)
        self.assertTrue(any(str(b).endswith("medico/widget") for b in bases))


if __name__ == "__main__":
    unittest.main()
