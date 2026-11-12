import itertools
import sys
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.authz import capability, capmap
from agenti.authz.risk import Risk

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustHomeRules")
DOMAINS = sorted(set(capability.HA_DOMAIN) | capability.HA_READ_PRIVATE | capmap.APPLIANCES | capmap.CLIMATE
                 | {"sensor", "mystery", ""})
SERVICES = ["turn_on", "turn_off", "toggle", "unlock", "open", "lock", "alarm_disarm", "alarm_arm_away",
            "alarm_arm_home", "open_cover", "close_cover", "set_cover_position", "stop_cover", "open_valve",
            "close_valve", "set_temperature", "trigger", ""]
CLASSES = ["", "garage", "gate", "door", "curtain", "blind"]
TEMPERATURES = [None, "21", 18, 24.0, 17.9, 24.5, "abc", float("nan"), float("inf"), 10 ** 400, [1]]
ENTITIES = {
    "light.salotto": {"device_class": ""},
    "lock.ingresso": {},
    "cover.garage": {"device_class": "garage"},
    "cover.tenda": {"device_class": "curtain"},
    "cover.strano": {"device_class": ["gate"]},
    "climate.casa": {},
    "valve.acqua": {},
}


def lookup(entity_id):
    return ENTITIES.get(entity_id)


@unittest.skipUnless(READY, "modulo nativo authz-core non installato")
class HomeRiskParityTest(unittest.TestCase):

    def setUp(self):
        self.assertIsNotNone(capability.native_rules())

    def test_service_risk_and_capabilities_match_for_every_combination(self):
        for declared, domain, service, device_class in itertools.product(DOMAINS, DOMAINS, SERVICES, CLASSES):
            entity = f"{domain}.x" if domain else ""
            local = {entity: {"device_class": device_class}} if entity else {}
            args = {"domain": declared, "service": service, "entity_id": entity}
            with self.subTest(declared=declared, domain=domain, service=service, device_class=device_class):
                self.assertEqual(capability.ha_service(args, local.get), capability._py_ha_service(args, local.get))
                self.assertEqual(capmap.ha_service(args, local.get), capmap._py_ha_service(args, local.get))

    def test_temperatures_choose_the_same_climate_capability(self):
        for domain, temperature in itertools.product(sorted(capmap.CLIMATE), TEMPERATURES):
            for args in ({"domain": domain, "service": "set_temperature", "entity_id": f"{domain}.casa",
                          "data": {"temperature": temperature}},
                         {"domain": domain, "service": "set_temperature", "temperature": temperature}):
                with self.subTest(domain=domain, temperature=temperature, nested="data" in args):
                    self.assertEqual(capmap.ha_service(args, lookup), capmap._py_ha_service(args, lookup))

    def test_multiple_targets_and_raw_formats_match(self):
        cases = [
            {"domain": "light", "service": "turn_on", "entity_id": "light.salotto, lock.ingresso,cover.garage"},
            {"domain": "cover", "service": "open_cover", "entity_id": ["cover.garage", "cover.tenda", " "]},
            {"domain": "LIGHT", "service": " UNLOCK ", "entity_id": ("lock.ingresso", "Light.Salotto")},
            {"domain": "scene", "service": "turn_on", "entity_id": 42},
            {"domain": None, "service": None, "entity_id": None},
            {"service": "open_valve", "entity_id": "valve.acqua"},
            {"domain": "script", "service": "turn_on", "entity_id": "nodot"},
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(capability.ha_service(args, lookup), capability._py_ha_service(args, lookup))
                self.assertEqual(capmap.ha_service(args, lookup), capmap._py_ha_service(args, lookup))

    def test_reads_match(self):
        for raw in ["person.nunzio", "sensor.t", "sensor.t, lock.a", ["zone.home", "light.x"], "", None, 3,
                    [f"{d}.x" for d in DOMAINS]]:
            with self.subTest(raw=raw):
                args = {"entity_id": raw}
                self.assertEqual(capability.ha_read(args), capability._py_ha_read(args))
                self.assertEqual(capmap.ha_read(args), capmap._py_ha_read(args))

    def test_non_string_device_class_is_not_sensitive(self):
        args = {"domain": "cover", "service": "open_cover", "entity_id": "cover.strano"}
        self.assertEqual(capability.ha_service(args, lookup), Risk.HOME)
        self.assertEqual(capmap.ha_service(args, lookup), ["home.cover.set"])

    def test_oversized_requests_fail_closed(self):
        many = ",".join(f"light.l{i}" for i in range(NATIVE.RustHomeRules.max_targets() + 1))
        args = {"domain": "light", "service": "turn_on", "entity_id": many}
        self.assertEqual(capability.ha_service(args, lookup), Risk.CRITICAL)
        self.assertEqual(capmap.ha_service(args, lookup), ["risk.critical"])
        long = {"domain": "light", "service": "x" * 300, "entity_id": "light.salotto"}
        self.assertEqual(capability.ha_service(long, lookup), Risk.CRITICAL)

    def test_plans_match(self):
        plan = {"kind": "query", "entities": ["person.nunzio"],
                "calls": [{"domain": "cover", "service": "open_cover", "entity_ids": ["cover.garage"]},
                          {"domain": "climate", "service": "set_temperature", "entity_ids": ["climate.casa"],
                           "data": {"temperature": 21}}, "junk"]}
        self.assertEqual(capability.plan_risk(plan, lookup), Risk.CRITICAL)
        self.assertEqual(capmap.of_plan(plan, lookup),
                         ["home.climate.adjust", "home.gate.open", "home.private.read"])


class HomeRiskFallbackTest(unittest.TestCase):

    def test_python_fallback_still_answers(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            args = {"domain": "lock", "service": "unlock", "entity_id": "lock.ingresso"}
            self.assertEqual(capability.ha_service(args, lookup), Risk.CRITICAL)
            self.assertEqual(capmap.ha_service(args, lookup), ["home.lock.unlock"])
            self.assertEqual(capability.ha_read({"entity_id": "camera.x"}), Risk.PERSONAL)
            self.assertEqual(capmap.ha_read({"entity_id": "sensor.x"}), ["home.state.read"])


if __name__ == "__main__":
    unittest.main()
