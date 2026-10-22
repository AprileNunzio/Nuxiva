import tempfile
import unittest
import unittest.mock
from pathlib import Path

from features.experts import templates
from features.experts.model import build
from features.fleet import mirror
from features.fleet.service import FleetService


def expert(template: str, expert_id: str):
    from features.experts import service
    return build(templates.blueprint(template, "it", expert_id), service.known_tools())


class MirrorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = FleetService(Path(self.tmp.name) / "fleet")
        patch = unittest.mock.patch.object(mirror, "SEEN", Path(self.tmp.name) / "mirrored.json")
        patch.start()
        self.addCleanup(patch.stop)

    def test_every_catalogue_expert_becomes_a_fleet_agent(self):
        from features.agent import registry
        registry.refresh()
        rows = [expert(tid, tid) for tid in templates.ids()]
        self.assertEqual(mirror.mirror(rows, self.service), len(rows))
        listing = self.service.store.list(__import__("features.fleet.store", fromlist=["Filter"]).Filter("", "", "", "", "", "", ""), "", 200)
        self.assertGreaterEqual(len(listing["items"]), 100)

    def test_mirroring_is_idempotent_and_respects_deletions(self):
        row = expert("lawyer", "lawyer")
        self.assertEqual(mirror.mirror([row], self.service), 1)
        self.assertEqual(mirror.mirror([row], self.service), 0)
        self.service.store.delete(mirror.spec_of(row).id)
        self.assertEqual(mirror.mirror([row], self.service), 0)

    def test_agent_carries_role_purpose_and_existing_tools_only(self):
        from features.agent import registry
        registry.refresh()
        row = expert("web-developer", "web-developer")
        mirror.mirror([row], self.service)
        record = self.service.store.get(mirror.spec_of(row).id)
        self.assertEqual(record["name"], row.role)
        self.assertEqual(record["origin"], "nuxiva")
        self.assertIn("web_research", record["tools"])
        self.assertTrue(set(record["tools"]) <= set(registry.TOOLS))


if __name__ == "__main__":
    unittest.main()
