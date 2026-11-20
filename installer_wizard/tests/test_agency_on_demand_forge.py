import json
import unittest

from agenti.agency import on_demand_forge, project_room
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import capability_dispatcher


class TestAgencyOnDemandForge(unittest.IsolatedAsyncioTestCase):
    def test_scopa_game_on_demand_workflow(self):
        gov = on_demand_forge.OnDemandCapabilityGovernor()
        user_query = "Nuxiva vogliamo giocare a Scopa?"

        self.assertFalse(gov.check_capability_available("scopa"))

        res = gov.request_capability(user_query=user_query, person_slug="nunzio")
        self.assertFalse(res["available"])
        self.assertEqual(res["capability"], "scopa")
        self.assertIn("Direttore CEO", res["message"])
        self.assertIn("Scopa", res["message"])
        self.assertTrue(res["proactive_callback_hook"])

        room = project_room.get_project_room(res["project_id"])
        self.assertIsNotNone(room)
        self.assertIn("Scopa", room["title"])

        complete_res = gov.complete_forge(
            "scopa",
            artifact_data={"game_type": "cards_napoletane", "rules": "scopa_classica"},
            custom_ready_message="Il gioco della Scopa è pronto! Ho mescolato le carte, a te la prima mossa.",
        )
        self.assertEqual(complete_res["status"], "published")
        self.assertEqual(complete_res["notified_callbacks_count"], 1)
        self.assertIn("prima mossa", complete_res["ready_message"])
        self.assertEqual(complete_res["widget"]["style"], "borderless_glassmorphic")

        self.assertTrue(gov.check_capability_available("scopa"))
        second_req = gov.request_capability("avvia scopa", person_slug="nunzio")
        self.assertTrue(second_req["available"])
        self.assertEqual(second_req["action"], "launch_directly")

    async def test_capability_dispatcher_tools(self):
        ctx = Context(project_id="test_p", folder=".")
        raw_res = await capability_dispatcher._dispatch_capability_request(ctx, {
            "query": "simulatore moto parabolico per compiti fisica",
            "person_slug": "figlio",
            "channel": "voice",
        })
        res = json.loads(raw_res)
        self.assertFalse(res["available"])
        self.assertIn("Direttore CEO", res["message"])

        raw_complete = await capability_dispatcher._notify_capability_completed(ctx, {
            "capability_name": res["capability"],
            "artifact_data": {"equations": ["s = v0*t + 0.5*a*t^2"]},
        })
        comp = json.loads(raw_complete)
        self.assertEqual(comp["status"], "published")


if __name__ == "__main__":
    unittest.main()
