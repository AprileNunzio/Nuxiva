import importlib.util
import unittest

from server.core.gliner_extractor.gliner_inference import GlinerSlotExtractor
from server.core.gliner_extractor.slot_validator import validate_slots
from server.tests.cortex_support import requires_native

SCHEMA = [
    {"name": "target_device", "entity_label": "dispositivo", "data_type": "text", "required": True},
    {"name": "volume_level", "entity_label": "volume", "data_type": "number", "required": False},
    {"name": "room", "entity_label": "stanza", "data_type": "enumeration", "required": False, "allowed_values": ["salotto", "cucina"]},
]


@requires_native
class SlotValidatorTests(unittest.TestCase):
    def test_extraction_is_typed_and_sanitised(self):
        result = validate_slots(SCHEMA, {"target_device": " lampada​ ", "volume_level": "30", "room": "cucina"}).unwrap()
        self.assertEqual(result, {"target_device": "lampada", "volume_level": 30.0, "room": "cucina"})

    def test_violations_are_returned_as_translated_failures(self):
        missing = validate_slots(SCHEMA, {"volume_level": "3"}, "it")
        self.assertEqual(missing.error.code, "cortex.slots.required_missing")
        self.assertIn("obbligatorio", missing.error.message)
        self.assertEqual(validate_slots(SCHEMA, {"target_device": "x", "extra": "y"}).error.code, "cortex.slots.unknown")
        self.assertEqual(validate_slots(SCHEMA, {"target_device": "x", "volume_level": "alto"}).error.code, "cortex.slots.type_mismatch")
        self.assertEqual(validate_slots(SCHEMA, {"target_device": "x", "room": "garage"}).error.code, "cortex.slots.value_not_allowed")

    def test_unserialisable_schema_is_rejected(self):
        self.assertEqual(validate_slots([{"name": {1, 2}}], {}).error.code, "cortex.slots.schema_invalid")


class EntityAssignmentTests(unittest.TestCase):
    def test_best_scoring_entity_wins_for_each_slot(self):
        entities = [
            {"label": "dispositivo", "text": "lampada", "score": 0.61},
            {"label": "dispositivo", "text": "lampada del tavolo", "score": 0.93},
            {"label": "volume", "text": "30", "score": 0.7},
            {"label": "irrilevante", "text": "x", "score": 0.99},
        ]
        assigned = GlinerSlotExtractor._assign(SCHEMA, entities)
        self.assertEqual(assigned, {"target_device": "lampada del tavolo", "volume_level": "30"})


@unittest.skipIf(importlib.util.find_spec("gliner") is not None, "GLiNER is installed in this environment")
class MissingModelTests(unittest.TestCase):
    def test_absent_gliner_is_reported_explicitly_and_remembered(self):
        extractor = GlinerSlotExtractor()
        first = extractor.extract("accendi la lampada", SCHEMA)
        self.assertEqual(first.error.code, "gliner.unavailable")
        self.assertIs(extractor.extract("accendi la lampada", SCHEMA).error, first.error)


if __name__ == "__main__":
    unittest.main()
