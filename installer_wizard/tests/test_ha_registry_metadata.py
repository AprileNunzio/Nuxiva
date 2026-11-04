import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.home_assistant.home import HomeBrain
from features.home_assistant.db import HomeDB


class RegistryMetadataTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with mock.patch("features.home_assistant.db.DB_FILE", Path(folder.name) / "home.db"):
            self.db = HomeDB()
        self.addCleanup(self.db.conn.close)
        with mock.patch("features.home_assistant.home.HomeDB", return_value=self.db):
            self.home = HomeBrain()

    def test_external_metadata_persists_and_reloads_without_losing_devices(self):
        cases = [(None, ""), ([], ""), (["1.2", "3.4"], "1.2, 3.4"),
                 (0, "0"), (2.5, "2.5"), ("v1", "v1"), ({"build": 4}, '{"build": 4}')]
        devices = [{"id": str(i), "name": "Device " + str(i), "sw_version": raw, "hw_version": raw,
                    "manufacturer": ["Maker", "Division"], "model": 123, "model_id": {"sku": "A"}}
                   for i, (raw, _) in enumerate(cases)]
        self.home._ingest(cfg={}, floors=[], areas=[], devices=devices,
                          entities=[{"entity_id": "light.test", "device_id": "0"}], entries=[],
                          states=[{"entity_id": "light.test", "state": "on", "attributes": {}}],
                          services={}, extended={})
        self.home._persist_registries()
        rows = self.db.query("SELECT device_id, sw_version, hw_version FROM devices ORDER BY device_id")
        self.assertEqual(rows, [(str(i), expected, expected) for i, (_, expected) in enumerate(cases)])
        self.assertEqual(self.db.query("SELECT count(*) FROM entities"), [(1,)])
        with mock.patch("features.home_assistant.home.HomeDB", return_value=self.db):
            restored = HomeBrain()
        self.assertEqual(len(restored.devices), len(cases))
        self.assertEqual(restored.devices["2"]["sw_version"], "1.2, 3.4")
        self.assertFalse(restored.online)

    def test_empty_registry_is_not_online_in_demo_environment(self):
        self.assertFalse(self.home.online)
        self.assertEqual(self.home.devices, {})
        self.assertEqual(self.home.entities, {})
