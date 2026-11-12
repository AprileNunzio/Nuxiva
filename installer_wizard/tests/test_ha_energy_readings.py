import unittest
from types import SimpleNamespace
from unittest import mock

from features.home_assistant.api import admin_home_energy


class EnergyReadingsTest(unittest.IsolatedAsyncioTestCase):
    async def readings(self, readings, online=True):
        brain = SimpleNamespace(online=online, entities={}, states={})
        for index, (value, unit) in enumerate(readings):
            eid = f"sensor.power_{index}"
            brain.entities[eid] = {"domain": "sensor", "name": eid}
            brain.states[eid] = {"state": value, "attrs": {"unit_of_measurement": unit}}
        with mock.patch("features.home_assistant.api.home.brain", brain):
            return await admin_home_energy()

    async def test_empty_or_partial_data_never_invents_whole_home_totals(self):
        for readings in ([], [(120, "W"), (240, "W")]):
            out = await self.readings(readings)
            self.assertEqual(out["summary"], {"total_power_w": None, "total_solar_w": None, "net_power_w": None})

    async def test_real_zero_units_and_unavailable_states(self):
        out = await self.readings([(0, "W"), (2, "kW"), (3, "mW"), (4, "MW"),
                                   ("unavailable", "W"), ("nan", "W"), ("inf", "W"), (2, "MWh")])
        watts = {s["entity_id"]: s["power_w"] for s in out["power_sensors"]}
        self.assertEqual(watts, {"sensor.power_0": 0, "sensor.power_1": 2000,
                                "sensor.power_2": 0.003, "sensor.power_3": 4000000,
                                "sensor.power_4": None, "sensor.power_5": None, "sensor.power_6": None})
        self.assertEqual(out["energy_sensors"][0]["energy_kwh"], 2000)

    async def test_disconnected_cache_is_not_a_current_reading(self):
        out = await self.readings([(120, "W")], online=False)
        self.assertIsNone(out["power_sensors"][0]["power_w"])
