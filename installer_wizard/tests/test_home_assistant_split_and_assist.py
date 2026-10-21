import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend.app_scanner import is_application, is_feature
from features.home_assistant.custom_assist import (
    eval_simple_jinja,
    load_custom_sentences,
    match_and_eval,
)
from features.home_assistant.home import brain
from features.home_assistant import tools as ha_tools


class HomeAssistantSplitAndAssistTest(unittest.IsolatedAsyncioTestCase):
    def test_app_and_feature_separation(self):
        """Verifica la separazione netta tra Applicazione (app) e Funzionalità (feature)."""
        app_manifest = {
            "id": "home_assistant",
            "name": "Home Assistant",
            "kind": "app",
            "scope": "apps/home_assistant",
        }
        feature_manifest = {
            "id": "home_assistant",
            "name": "Casa (Home Assistant)",
            "kind": "feature",
            "scope": "features/home_assistant",
        }

        self.assertTrue(is_application(app_manifest, "client_web/src/apps/home_assistant/manifest.json"))
        self.assertFalse(is_feature(app_manifest, "client_web/src/apps/home_assistant/manifest.json"))

        self.assertFalse(is_application(feature_manifest, "installer_wizard/features/home_assistant/feature.json"))
        self.assertTrue(is_feature(feature_manifest, "installer_wizard/features/home_assistant/feature.json"))

    def test_custom_assist_yaml_scanner_and_evaluation(self):
        """Verifica che /config/custom_sentences/it/energia.yaml e /config/packages/custom_assist_energia.yaml
        vengano letti e valutati sui sensori reali."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            cs_dir = config_dir / "custom_sentences" / "it"
            cs_dir.mkdir(parents=True)
            pkg_dir = config_dir / "packages"
            pkg_dir.mkdir(parents=True)

            # 1. Crea /config/custom_sentences/it/energia.yaml
            energia_yaml = """
language: "it"
intents:
  ConsumoCasaAssist:
    data:
      - sentences:
          - "quanto sta assorbendo tutta la casa"
          - "quanto consuma la casa"
          - "assorbimento casa"
"""
            (cs_dir / "energia.yaml").write_text(energia_yaml, encoding="utf-8")

            # 2. Crea /config/packages/custom_assist_energia.yaml
            assist_pkg_yaml = """
intent_script:
  ConsumoCasaAssist:
    speech:
      text: "In questo momento la casa sta assorbendo {{ states('sensor.potenza_totale_consumata') }} Watt."
"""
            (pkg_dir / "custom_assist_energia.yaml").write_text(assist_pkg_yaml, encoding="utf-8")

            # Scansiona
            loaded = load_custom_sentences(config_dir)
            self.assertIn("ConsumoCasaAssist", loaded["intents"])
            self.assertIn("ConsumoCasaAssist", loaded["responses"])
            self.assertIn("quanto sta assorbendo tutta la casa", loaded["intents"]["ConsumoCasaAssist"]["sentences"])

            # Valuta con stati reali
            mock_states = {
                "sensor.potenza_totale_consumata": {"state": "1420", "attrs": {"unit_of_measurement": "W"}},
            }
            speech = match_and_eval("quanto sta assorbendo tutta la casa?", mock_states, config_dir=config_dir, language="it")
            self.assertIsNotNone(speech)
            self.assertIn("1420", speech)
            self.assertIn("In questo momento la casa sta assorbendo 1420 Watt.", speech)

    def test_eval_simple_jinja_extracts_real_sensor_values(self):
        states = {
            "sensor.potenza_casa": {"state": "850"},
            "sensor.produzione_solare": {"state": "3200"},
        }
        template = "Assorbimento: {{ states('sensor.potenza_casa') }} W, Solare: {{ states('sensor.produzione_solare') }} W."
        res = eval_simple_jinja(template, states)
        self.assertEqual(res, "Assorbimento: 850 W, Solare: 3200 W.")

    async def test_ask_assist_fallback_to_custom_yaml(self):
        """Verifica che ask_assist risponda con i custom sentences reali."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            cs_dir = config_dir / "custom_sentences" / "it"
            cs_dir.mkdir(parents=True)
            pkg_dir = config_dir / "packages"
            pkg_dir.mkdir(parents=True)

            (cs_dir / "energia.yaml").write_text("""
language: "it"
intents:
  Energia:
    data:
      - sentences:
          - "quanto sta assorbendo tutta la casa"
""", encoding="utf-8")

            (pkg_dir / "custom_assist_energia.yaml").write_text("""
intent_script:
  Energia:
    speech:
      text: "La casa assorbe {{ states('sensor.house_power') }} Watt."
""", encoding="utf-8")

            brain.states["sensor.house_power"] = {"state": "980", "attrs": {"unit_of_measurement": "W"}}
            with mock.patch.object(brain, "settings", return_value={"url": "", "token": "", "config_dir": str(config_dir)}):
                result = await brain.ask_assist("quanto sta assorbendo tutta la casa?")
                self.assertTrue(result["ok"])
                self.assertIn("980 Watt", result["speech"])
                self.assertEqual(result["source"], "custom_yaml")

    async def test_commands_handle_missing_sensor_delegates_to_assist(self):
        """Verifica che handle invochi Assist quando una query di lettura o frase non è risolta localmente."""
        brain.entities["sensor.dummy"] = {"entity_id": "sensor.dummy", "name": "Dummy", "domain": "sensor"}
        with mock.patch.object(brain, "ask_assist", return_value={"ok": True, "speech": "La casa sta assorbendo 1350 Watt.", "source": "ha_assist_ws"}):
            with mock.patch.object(brain, "settings", return_value={"enabled": True, "url": "http://ha:8123", "token": "x", "confirm": False}):
                res = await brain.handle("quanto sta assorbendo tutta la casa?")
                self.assertIsNotNone(res)
                speech, ui, tag = res
                self.assertIn("1350 Watt", speech)
                self.assertIn("assist", tag)

    async def test_mcp_tools_registration_and_execution(self):
        """Verifica la corretta registrazione ed esecuzione dei tool MCP di Home Assistant."""
        # ha_get_state
        brain.entities["light.soggiorno"] = {"entity_id": "light.soggiorno", "name": "Luce Soggiorno", "domain": "light"}
        brain.states["light.soggiorno"] = {"state": "on", "attrs": {"brightness": 200}, "lc": 1000}
        st = ha_tools.ha_get_state("light.soggiorno")
        self.assertEqual(st["state"], "on")
        self.assertEqual(st["name"], "Luce Soggiorno")

        # ha_list_entities
        listed = ha_tools.ha_list_entities("light")
        self.assertTrue(any(e["entity_id"] == "light.soggiorno" for e in listed))

        # ha_energy_consumption
        brain.entities["sensor.potenza_casa"] = {"entity_id": "sensor.potenza_casa", "name": "Potenza casa", "domain": "sensor"}
        brain.states["sensor.potenza_casa"] = {"state": "1200", "attrs": {"unit_of_measurement": "W", "device_class": "power"}}
        with mock.patch.object(brain, "ask_assist", return_value={"ok": False}):
            en = await ha_tools.ha_energy_consumption()
            self.assertGreaterEqual(en["total_power_w"], 1200)

        # ha_devices_by_room
        brain.areas["area_salotto"] = {"area_id": "area_salotto", "name": "Salotto", "floor_id": "p0"}
        brain.floors["p0"] = {"floor_id": "p0", "name": "Piano Terra"}
        brain.area_entities["area_salotto"] = ["light.soggiorno"]
        rooms_res = ha_tools.ha_devices_by_room()
        self.assertIn("rooms", rooms_res)
        self.assertTrue(any(r["room"] == "Salotto" for r in rooms_res["rooms"]))


if __name__ == "__main__":
    unittest.main()
