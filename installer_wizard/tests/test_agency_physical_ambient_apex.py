import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.agency.ambient_fusion import AmbientSensorReading, PresenceSignal, ambient_fusion
from agenti.agency.physical_actuation import physical_actuator
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import ambient_sensors, habit_governor as habit_tools, physical_actuator as actuator_tools
from agenti.people import people, private_store


class TestAgencyPhysicalAmbientApex(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.people_dir = Path(self.tmp.name) / "people"
        self.people_dir.mkdir(parents=True, exist_ok=True)
        self.patchers = [
            mock.patch.object(people, "PEOPLE_DIR", self.people_dir),
            mock.patch.object(private_store, "KEY_FILE", self.people_dir / "people.key"),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmp.cleanup()

    async def test_ambient_presence_ingestion_and_sensor_fusion(self):
        people.ensure("nunzio", "Nunzio Aprile")
        people.update("nunzio", {"wake_time": "06:00", "sleep_time": "23:00"})

        room_id = "living_room"
        sig = PresenceSignal(
            source_kind="camera_ir_face",
            detected_slug="nunzio",
            confidence=0.92,
            room_id=room_id,
        )
        res = ambient_fusion.ingest_presence_signal(sig)
        self.assertEqual(res["dominant_person"], "nunzio")
        self.assertIn("nunzio", res["occupants"])

        reading = AmbientSensorReading(
            sensor_id="bme680_temp",
            kind="temperature",
            value=21.8,
            unit="C",
            room_id=room_id,
        )
        ambient_fusion.ingest_sensor_reading(reading)

        ctx = Context(project_id="p1", folder=".")
        raw_state = await ambient_sensors._get_ambient_room_state(ctx, {"room_id": room_id})
        state = json.loads(raw_state)
        self.assertTrue(state["is_occupied"])
        self.assertEqual(state["dominant_person"], "nunzio")
        self.assertEqual(state["metrics"]["temperature"]["value"], 21.8)

    async def test_physical_actuation_presets_and_commands(self):
        ctx = Context(project_id="p1", folder=".")
        raw = await actuator_tools._set_room_preset_scene(ctx, {
            "scene_name": "bedtime_calm_dreamscape",
            "room_id": "bedroom_kids",
        })
        res = json.loads(raw)
        self.assertEqual(res["status"], "scene_applied")
        self.assertEqual(res["scene"], "bedtime_calm_dreamscape")

        state = physical_actuator.active_room_states["bedroom_kids"]
        self.assertEqual(state["lights"]["brightness"], 12)
        self.assertEqual(state["lights"]["color_temp_k"], 2000)
        self.assertTrue(state["audio"]["playing"])
        self.assertIn("delta_waves", state["audio"]["track"])

        raw_cmd = await actuator_tools._dispatch_physical_command(ctx, {
            "domain": "climate",
            "target_id": "thermostat_zone_1",
            "action": "set_temperature",
            "parameters": {"temperature": 20.5, "mode": "eco"},
            "room_id": "bedroom_kids",
        })
        cmd_res = json.loads(raw_cmd)
        self.assertEqual(cmd_res["status"], "executed")
        self.assertEqual(cmd_res["resulting_state"]["climate"]["target_temp_c"], 20.5)

    async def test_continuous_habit_reinforcement_and_consolidation(self):
        people.ensure("angelika", "Angelika Aprile")
        ctx = Context(project_id="p1", folder=".")

        raw_conf1 = await habit_tools._query_habit_confidence(ctx, {
            "person_slug": "angelika",
            "habit_key": "favorite_tea",
        })
        self.assertEqual(json.loads(raw_conf1)["confidence"], 0.5)

        await habit_tools._record_habit_feedback(ctx, {
            "person_slug": "angelika",
            "habit_key": "favorite_tea",
            "value": "camomilla vaniglia",
            "feedback": "accepted",
        })
        await habit_tools._record_habit_feedback(ctx, {
            "person_slug": "angelika",
            "habit_key": "favorite_tea",
            "value": "camomilla vaniglia",
            "feedback": "confirm",
        })
        raw_final = await habit_tools._record_habit_feedback(ctx, {
            "person_slug": "angelika",
            "habit_key": "favorite_tea",
            "value": "camomilla vaniglia",
            "feedback": "positive",
        })
        res_final = json.loads(raw_final)
        self.assertTrue(res_final["is_autonomous"])
        self.assertGreaterEqual(res_final["confidence"], 0.85)

        updated_p = people.load("angelika")
        self.assertEqual(updated_p.get("favorite_tea"), "camomilla vaniglia")


if __name__ == "__main__":
    unittest.main()
