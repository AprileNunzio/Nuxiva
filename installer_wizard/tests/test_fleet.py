import tempfile
import unittest
import unittest.mock
from pathlib import Path

from features.fleet import catalog
from features.fleet.model import FleetError, build_spec, clean_text, slug
from features.fleet.service import FleetService
from features.fleet.shards import SHARDS, shard_of
from features.fleet.store import Filter, FleetStore, decode_cursor, encode_cursor


def spec(agent_id: str, **extra):
    return build_spec({"id": agent_id, "name": extra.pop("name", agent_id), **extra}, "user")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FleetStore(Path(self.tmp.name))

    def test_create_get_and_duplicate(self):
        self.store.create(spec("garden-eye", instructions="segreto del giardino"))
        record = self.store.get("garden-eye")
        self.assertEqual(record["instructions"], "segreto del giardino")
        with self.assertRaises(FleetError) as caught:
            self.store.create(spec("garden-eye"))
        self.assertEqual(caught.exception.code, "exists")

    def test_instructions_are_encrypted_on_disk(self):
        self.store.create(spec("vault-keeper", instructions="PAROLA-RISERVATA-XYZ"))
        blob = b"".join(path.read_bytes() for path in Path(self.tmp.name).glob("shard_*.db*"))
        self.assertNotIn(b"PAROLA-RISERVATA-XYZ", blob)
        self.assertEqual((Path(self.tmp.name) / "fleet.key").stat().st_mode & 0o777, 0o600)

    def test_pagination_visits_every_agent_once_across_shards(self):
        ids = [f"unit-{n:04d}" for n in range(300)]
        self.assertEqual(self.store.create_many([spec(i) for i in ids]), 300)
        seen, cursor = [], ""
        while True:
            page = self.store.list(Filter(), cursor, 37)
            seen.extend(item["id"] for item in page["items"])
            cursor = page["next"]
            if not page["more"]:
                break
        self.assertEqual(sorted(seen), ids)
        self.assertEqual(len(set(seen)), 300)
        self.assertGreater(len({shard_of(i) for i in ids}), 50)

    def test_summary_counts_follow_every_change(self):
        self.store.create_many([spec(f"cnt-{n:03d}", kind="home") for n in range(10)])
        self.assertEqual(self.store.summary()["total"], 10)
        self.store.update("cnt-001", {"state": "paused"})
        self.store.delete("cnt-002")
        summary = self.store.summary()
        self.assertEqual((summary["total"], summary["state"]["paused"], summary["state"]["active"]), (9, 1, 8))
        self.assertEqual(summary["kind"]["home"], 9)

    def test_filters_prefix_and_links(self):
        self.store.create_many([spec("alpha-one", name="Alpha One"), spec("beta-two", name="Beta Two", kind="media")])
        self.store.link("beta-two", "tool", ["play_music"])
        self.store.link("beta-two", "widget", ["clock"])
        self.assertEqual([i["id"] for i in self.store.list(Filter(prefix="alp"))["items"]], ["alpha-one"])
        self.assertEqual([i["id"] for i in self.store.list(Filter(kind="media"))["items"]], ["beta-two"])
        self.assertEqual([i["id"] for i in self.store.list(Filter(tool="play_music"))["items"]], ["beta-two"])
        self.assertEqual(self.store.list(Filter(widget="clock"))["items"][0]["tools"], ["play_music"])
        self.store.unlink("beta-two", "tool", "play_music")
        self.assertEqual(self.store.list(Filter(tool="play_music"))["items"], [])

    def test_bulk_state_is_bounded_and_counted(self):
        self.store.create_many([spec(f"bulk-{n:03d}") for n in range(40)])
        outcome = self.store.change_state(Filter(), "archived", 25)
        self.assertEqual(outcome, {"changed": 25, "more": True})
        summary = self.store.summary()
        self.assertEqual((summary["state"]["archived"], summary["state"]["active"]), (25, 15))

    def test_hostile_input_is_rejected(self):
        for bad in ("../x", "A", "x" * 80, "a b", "a;drop"):
            with self.assertRaises(FleetError):
                self.store.get(bad)
        with self.assertRaises(FleetError):
            decode_cursor("not-a-cursor")
        with self.assertRaises(FleetError):
            decode_cursor(encode_cursor(SHARDS + 1, "valid-id"))
        self.store.create(spec("safe-one"))
        injected = self.store.list(Filter(prefix="'; DROP TABLE agents; --"))
        self.assertEqual(injected["items"], [])
        self.assertEqual(self.store.get("safe-one")["id"], "safe-one")

    def test_sanitising(self):
        self.assertEqual(clean_text("<b>ciao</b>\x00 mondo", 50), "bciao/b mondo")
        self.assertEqual(slug("Giardino d'Èrica!"), "giardino-d-erica")
        self.assertEqual(clean_text(5, 10), "")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = FleetService(Path(self.tmp.name))
        self.tools = {"play_music": {"description": "riproduce musica"}, "list_lights": {"description": "elenca le luci della casa"}}
        self.widgets = {"clock": {"name": "Orologio", "description": "mostra l'ora"}}
        self.patches = [unittest.mock.patch.object(catalog, "_registry", lambda: self.tools),
                        unittest.mock.patch.object(catalog, "_widgets", lambda: self.widgets)]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_create_validates_tools_and_widgets(self):
        record = self.service.create({"name": "Musica", "tools": ["play_music"], "widgets": ["clock"]}, "user", "nunzio")
        self.assertEqual((record["tools"], record["widgets"], record["id"]), (["play_music"], ["clock"], "musica"))
        with self.assertRaises(FleetError) as caught:
            self.service.create({"name": "Fantasma", "tools": ["ghost_tool"]}, "user", "nunzio")
        self.assertEqual(caught.exception.code, "unknown_tool")
        self.assertFalse(self.service.store.exists("fantasma"))

    def test_unique_id_and_suggestions(self):
        self.service.create({"name": "Luci"}, "user", "nunzio")
        self.assertEqual(self.service.unique_id("Luci"), "luci-2")
        self.assertEqual(catalog.suggest("accendere le luci della casa")["tools"], ["list_lights"])
        self.assertEqual(catalog.suggest("")["tools"], [])

    def test_detail_reports_dangling_links(self):
        self.service.create({"name": "Musica", "tools": ["play_music"]}, "user", "nunzio")
        del self.tools["play_music"]
        self.assertEqual(self.service.detail("musica")["missing_tools"], ["play_music"])


if __name__ == "__main__":
    unittest.main()
