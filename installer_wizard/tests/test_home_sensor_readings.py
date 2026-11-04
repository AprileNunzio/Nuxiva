import unittest
from unittest import mock

from features.home_assistant.answers import HomeAnswers
from features.home_assistant.live import HomeLive
from features.home_assistant.nlu.matching import Catalog
from features.home_assistant.nlu.parser import parse
from features.home_assistant.readings import messages
from features.home_assistant.registry import HomeRegistry


class SensorHome(HomeRegistry, HomeLive, HomeAnswers):
    def __init__(self):
        self.ha_name = "Casa"
        self.aliases, self.matter_net, self.last_motion = {}, {}, {}
        self.area_entities, self.catalog = {}, Catalog()
        self.occupied, self.rev = [], 0
        self._dirty_states, self._activity = {}, []
        self._resync = None
        self._ingest(cfg={}, floors=[], areas=[{"area_id": "bagno", "name": "Bagno"},
                                               {"area_id": "cucina", "name": "Cucina"}],
                     devices=[{"id": "clima", "name": "Clima bagno", "area_id": "bagno"},
                              {"id": "washer", "name": "Lavatrice", "area_id": "cucina"},
                              {"id": "pv", "name": "Fotovoltaico"}],
                     entities=[{"entity_id": "sensor.umidita", "device_id": "clima"},
                               {"entity_id": "sensor.temperatura", "device_id": "clima", "area_id": "cucina"},
                               {"entity_id": "sensor.washer_power", "device_id": "washer", "original_name": "Power"},
                               {"entity_id": "sensor.pv_power", "device_id": "pv"},
                               {"entity_id": "sensor.pv_energy", "device_id": "pv"},
                               {"entity_id": "sensor.house_power"}, {"entity_id": "sensor.house_energy"}],
                     entries=[], states=[self.state("sensor.umidita", "64", "humidity", "%", "Umidità"),
                                         self.state("sensor.temperatura", "20", "temperature", "°C", "Temperatura"),
                                         self.state("sensor.washer_power", "1250", "power", "W", "Potenza"),
                                         self.state("sensor.pv_power", "3.2", "power", "kW", "Potenza fotovoltaico"),
                                         self.state("sensor.pv_energy", "12.4", "energy", "kWh", "Fotovoltaico oggi"),
                                         self.state("sensor.house_power", "850", "power", "W", "Consumo casa"),
                                         self.state("sensor.house_energy", "1200", "energy", "kWh", "Energia casa totale")],
                     services={}, extended={})

    @staticmethod
    def settings():
        return {"room": "", "motion_min": 5}

    @staticmethod
    def state(entity_id, value, device_class, unit, name):
        return {"entity_id": entity_id, "state": value, "attributes": {"device_class": device_class,
                "unit_of_measurement": unit, "friendly_name": name}}

    def reply(self, text):
        query = parse(text, self.catalog)
        if query is None:
            raise AssertionError(f"query not recognized: {text}")
        with mock.patch("features.places.context.area", return_value=None):
            return query, self.answer(query)


class HomeSensorReadingsTest(unittest.TestCase):
    def setUp(self):
        self.home = SensorHome()

    def test_entity_inherits_device_area_but_explicit_area_wins(self):
        self.assertEqual(self.home.entities["sensor.umidita"]["area_id"], "bagno")
        self.assertEqual(self.home.entities["sensor.temperatura"]["area_id"], "cucina")
        self.assertIn("sensor.umidita", self.home.area_entities["bagno"])

    def test_humidity_question_uses_humidity_without_temperature(self):
        query, (speech, ui) = self.home.reply("qual è l'umidità del bagno?")
        self.assertEqual(query["metrics"], ["humidity"])
        self.assertIn("64 %", speech)
        self.assertNotIn("temperatura", speech.lower())
        self.assertEqual(ui["panels"][0]["items"][0]["label"], "Bagno")

    def test_temperature_value_ending_in_zero_is_preserved(self):
        _, (speech, _) = self.home.reply("quanti gradi ci sono in cucina?")
        self.assertIn("20 °C", speech)
        self.assertNotIn("Umidità", speech)

    def test_missing_humidity_never_reports_missing_temperature(self):
        _, (speech, _) = self.home.reply("qual è l'umidità della cucina?")
        self.assertIn("umidità non disponibile", speech)
        self.assertNotIn("temperatura", speech)

    def test_current_house_energy_question_reads_power_not_cumulative_energy(self):
        query, (speech, ui) = self.home.reply("quanta energia sta consumando la casa adesso?")
        self.assertEqual(query["metric"], "power")
        self.assertIn("850 W", speech)
        self.assertNotIn("1200", speech)
        self.assertEqual(len(ui["panels"][0]["items"]), 1)

    def test_solar_production_preserves_power_unit(self):
        _, (speech, _) = self.home.reply("quanto sta producendo il fotovoltaico?")
        self.assertIn("3.2 kW", speech)
        self.assertNotIn("1250", speech)

    def test_device_name_resolves_sensor_without_becoming_controllable(self):
        _, (speech, ui) = self.home.reply("quanti watt consuma la lavatrice?")
        self.assertIn("1250 W", speech)
        self.assertIn("Lavatrice", speech)
        self.assertFalse(self.home.catalog.entities["sensor.washer_power"]["controllable"])
        self.assertEqual(list(self.home.catalog.controllable()), [])
        self.assertEqual(ui["panels"][0]["items"][0]["entity_id"], "sensor.washer_power")
        self.assertIsNone(parse("accendi la lavatrice", self.home.catalog))

    def test_energy_period_uses_matching_sensor_and_rejects_total_as_today(self):
        query, (speech, _) = self.home.reply("quanta energia ha prodotto il fotovoltaico oggi?")
        self.assertEqual(query["metric"], "energy")
        self.assertIn("12.4 kWh", speech)
        _, (speech, _) = self.home.reply("quanta energia ha consumato la casa oggi?")
        self.assertEqual(speech, messages()["missing_reading"])

    def test_unknown_device_and_wrong_area_do_not_use_another_sensor(self):
        for request in ("quanti watt consuma il frigorifero?", "quanti watt consuma la lavatrice in bagno?"):
            with self.subTest(request=request):
                _, (speech, _) = self.home.reply(request)
                self.assertEqual(speech, messages()["missing_reading"])

    def test_multiple_sensors_are_reported_individually_without_a_total(self):
        self.home.catalog.entities["sensor.house_power_2"] = {
            **self.home.catalog.entities["sensor.house_power"], "entity_id": "sensor.house_power_2", "name": "Casa backup"}
        self.home.states["sensor.house_power_2"] = {"state": "900", "attrs": {"unit_of_measurement": "W"}}
        _, (speech, ui) = self.home.reply("quanta potenza consuma casa?")
        self.assertIn(messages()["multiple"], speech)
        self.assertIn("850 W", speech)
        self.assertIn("900 W", speech)
        self.assertEqual(len(ui["panels"][0]["items"]), 2)

    def test_unavailable_and_nonfinite_readings_are_never_reported_as_values(self):
        for value in ("unavailable", "unknown", "nan", "inf", "-inf", True, None):
            with self.subTest(value=value):
                self.home.states["sensor.washer_power"]["state"] = value
                _, (speech, _) = self.home.reply("quanti watt consuma la lavatrice?")
                self.assertIn(messages()["unavailable"], speech)
        self.home.states["sensor.umidita"]["state"] = "nan"
        _, (speech, _) = self.home.reply("umidità bagno")
        self.assertIn(messages()["missing_humidity"], speech)

    def test_reading_uses_live_state_and_does_not_reuse_deleted_sensor_value(self):
        self.home.states["sensor.washer_power"]["state"] = "0"
        _, (speech, _) = self.home.reply("quanti watt consuma la lavatrice?")
        self.assertIn("0 W", speech)
        self.home.states.pop("sensor.washer_power")
        _, (speech, _) = self.home.reply("quanti watt consuma la lavatrice?")
        self.assertIn(messages()["unavailable"], speech)

    def test_localized_reading_messages_have_matching_keys(self):
        keys = set(messages("it"))
        self.assertEqual(set(messages("en")), keys)
        self.assertEqual(set(messages("fr")), keys)
        self.assertEqual(set(messages("es")), keys)
        query = parse("quanti watt consuma la lavatrice?", self.home.catalog) | {"language": "en"}
        self.assertEqual(self.home.answer(query)[1]["title"], "Electrical power")

    def test_general_energy_questions_remain_available_to_conversation(self):
        for request in ("cos'è l'energia elettrica?", "spiegami la differenza tra energia e potenza",
                        "come risparmiare energia?"):
            with self.subTest(request=request):
                self.assertIsNone(parse(request, self.home.catalog))


if __name__ == "__main__":
    unittest.main()
