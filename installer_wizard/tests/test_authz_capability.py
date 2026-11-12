import asyncio
import unittest
from unittest import mock

from features.agent import registry
from features.authz import capability, gate
from features.authz.principal import ANONYMOUS, Principal, Strength, act_as, current
from features.authz.risk import Risk
from features.home_assistant.home import brain

ENTITIES = {
    "light.salotto": {"entity_id": "light.salotto", "domain": "light"},
    "lock.ingresso": {"entity_id": "lock.ingresso", "domain": "lock"},
    "cover.garage": {"entity_id": "cover.garage", "domain": "cover", "device_class": "garage"},
    "cover.tenda": {"entity_id": "cover.tenda", "domain": "cover", "device_class": "curtain"},
    "light.luce_porta": {"entity_id": "light.luce_porta", "domain": "light"},
}
GUEST = Principal(slug="", role="guest", strength=Strength.NONE)
OWNER_SINGLE = Principal(slug="nunzio", role="owner", strength=Strength.SINGLE)
OWNER_STRONG = Principal(slug="nunzio", role="owner", strength=Strength.STRONG)


def lookup(entity_id):
    return ENTITIES.get(entity_id)


class CapabilityRiskTests(unittest.TestCase):

    def call(self, domain, service, entity):
        return capability.ha_service({"domain": domain, "service": service, "entity_id": entity}, lookup)

    def test_lights_and_scenes_stay_in_the_home_level(self):
        self.assertEqual(self.call("light", "turn_on", "light.salotto"), Risk.HOME)
        self.assertEqual(self.call("scene", "turn_on", "scene.relax"), Risk.HOME)

    def test_unlocking_and_opening_sensitive_covers_is_critical(self):
        self.assertEqual(self.call("lock", "unlock", "lock.ingresso"), Risk.CRITICAL)
        self.assertEqual(self.call("cover", "open_cover", "cover.garage"), Risk.CRITICAL)
        self.assertEqual(self.call("alarm_control_panel", "alarm_disarm", "alarm_control_panel.casa"), Risk.CRITICAL)

    def test_locking_and_closing_a_garage_need_recognition(self):
        self.assertEqual(self.call("lock", "lock", "lock.ingresso"), Risk.PERSONAL)
        self.assertEqual(self.call("cover", "close_cover", "cover.garage"), Risk.PERSONAL)
        self.assertEqual(self.call("cover", "close_cover", "cover.tenda"), Risk.HOME)

    def test_the_entity_domain_wins_over_the_declared_domain(self):
        self.assertEqual(self.call("light", "unlock", "lock.ingresso"), Risk.CRITICAL)
        self.assertEqual(self.call("homeassistant", "turn_on", "light.salotto"), Risk.FILES)

    def test_the_riskiest_entity_decides(self):
        self.assertEqual(self.call("light", "turn_on", "light.salotto, lock.ingresso"), Risk.PERSONAL)

    def test_unknown_domains_are_not_home(self):
        self.assertEqual(self.call("qualcosa", "turn_on", ""), Risk.FILES)

    def test_reading_people_and_locks_is_personal(self):
        self.assertEqual(capability.ha_read({"entity_id": "person.nunzio"}), Risk.PERSONAL)
        self.assertEqual(capability.ha_read({"entity_id": "sensor.temperatura"}), Risk.HOME)

    def test_other_tools_keep_their_base_risk(self):
        self.assertEqual(capability.of_call("music_play", {"query": "jazz"}, Risk.HOME, lookup), Risk.HOME)

    def test_plans_take_the_riskiest_call(self):
        plan = {"kind": "command", "calls": [{"domain": "light", "service": "turn_on", "entity_ids": ["light.salotto"]},
                                             {"domain": "lock", "service": "unlock", "entity_ids": ["lock.ingresso"]}]}
        self.assertEqual(capability.plan_risk(plan, lookup), Risk.CRITICAL)


class GateWithArgumentsTests(unittest.TestCase):

    def tearDown(self):
        current.set(ANONYMOUS)

    def decide(self, principal, args):
        act_as(principal)
        with mock.patch.object(capability, "ha_lookup", side_effect=lookup):
            return gate.tool("ha_call_service", args)

    def test_a_guest_can_switch_on_a_light(self):
        self.assertTrue(self.decide(GUEST, {"domain": "light", "service": "turn_on", "entity_id": "light.salotto"}).allowed)

    def test_a_guest_cannot_unlock_the_door(self):
        self.assertFalse(self.decide(GUEST, {"domain": "lock", "service": "unlock", "entity_id": "lock.ingresso"}).allowed)

    def test_a_disguised_entity_name_does_not_help(self):
        self.assertFalse(self.decide(GUEST, {"domain": "light", "service": "unlock", "entity_id": "lock.ingresso"}).allowed)

    def test_the_owner_needs_face_and_voice_to_unlock(self):
        args = {"domain": "lock", "service": "unlock", "entity_id": "lock.ingresso"}
        self.assertFalse(self.decide(OWNER_SINGLE, args).allowed)
        self.assertTrue(self.decide(OWNER_STRONG, args).allowed)

    def test_generic_home_tools_are_no_longer_open_to_guests(self):
        act_as(GUEST)
        for name in ("run_automation", "toggle_automation", "emit_event", "agent_tell", "ceo_delegate", "ha_ask_assist"):
            self.assertFalse(gate.tool(name).allowed, name)


class AgentConfirmationTests(unittest.TestCase):

    def tearDown(self):
        current.set(ANONYMOUS)

    def test_sensitive_service_calls_require_confirmation(self):
        with mock.patch.object(capability, "ha_lookup", side_effect=lookup):
            self.assertTrue(registry.needs_confirm("ha_call_service", {"domain": "lock", "service": "unlock",
                                                                     "entity_id": "lock.ingresso"}))
            self.assertFalse(registry.needs_confirm("ha_call_service", {"domain": "light", "service": "turn_on",
                                                                      "entity_id": "light.salotto"}))

    def test_only_the_person_who_asked_can_confirm(self):
        from features.agent.agent import Agent
        agent = Agent()
        act_as(OWNER_STRONG)
        with mock.patch("features.agent.agent.session_key", return_value="k"):
            agent.pending["k"] = {"request": "apri", "steps": [], "tool": "ha_call_service", "at": 1e18, "who": "nunzio",
                                  "args": {"domain": "lock", "service": "unlock", "entity_id": "lock.ingresso"}}
            act_as(Principal(slug="anna", role="family", strength=Strength.STRONG))
            with mock.patch.object(agent, "_execute") as execute:
                reply = asyncio.run(agent.confirm(True))
        execute.assert_not_called()
        self.assertEqual(reply, gate.REFUSALS["role"])


class HomeCommandsGuardTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.saved = dict(brain.entities)
        brain.entities.update(ENTITIES)
        brain.pending = None

    def tearDown(self):
        brain.entities.clear()
        brain.entities.update(self.saved)
        brain.pending = None
        current.set(ANONYMOUS)

    def test_a_confirmation_from_another_voice_is_refused(self):
        brain.pending = {"plan": {"kind": "command", "calls": []}, "until": 1e18, "who": "nunzio"}
        act_as(GUEST)
        with mock.patch.object(brain, "settings", return_value={"enabled": True, "url": "http://ha", "token": "x", "confirm": True}), \
                mock.patch.object(brain, "_run") as run:
            speech, _, source = asyncio.run(brain.handle("conferma"))
        run.assert_not_called()
        self.assertEqual(speech, gate.REFUSALS["role"])
        self.assertIsNone(brain.pending)

    def test_a_guest_plan_to_unlock_is_refused_before_execution(self):
        act_as(GUEST)
        plan = {"kind": "command", "calls": [{"domain": "lock", "service": "unlock", "entity_ids": ["lock.ingresso"]}],
                "entities": ["lock.ingresso"], "sensitive": True}
        self.assertNotEqual(brain._refusal(plan, "sblocca la porta"), "")

    def test_a_guest_plan_for_lights_is_allowed(self):
        act_as(GUEST)
        plan = {"kind": "command", "calls": [{"domain": "light", "service": "turn_on", "entity_ids": ["light.salotto"]}],
                "entities": ["light.salotto"], "sensitive": False}
        self.assertEqual(brain._refusal(plan, "accendi la luce"), "")


if __name__ == "__main__":
    unittest.main()
