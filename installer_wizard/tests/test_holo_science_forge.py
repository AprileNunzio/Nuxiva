import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.hands.holo import exact, hd
from agenti.hands.holo.catalog import fetch, finder, judge
from agenti.hands.holo.catalog.store import Catalog
from agenti.hands.holo.forge import forge, meshy, node
from agenti.hands.holo.science import fallback, resolve, sources
from agenti.hands.holo.session import session

WATER = ("962\n  -OEChem-\n\n  3  2  0     0  0  0  0  0  0999 V2000\n"
         "    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
         "    0.2774    0.8929    0.2544 H   0  0  0  0  0  0  0  0  0  0  0  0\n"
         "    0.6068   -0.2383   -0.7169 H   0  0  0  0  0  0  0  0  0  0  0  0\n"
         "  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\nM  END\n$$$$\n")
CAFFEINE_LIKE = WATER.replace("  3  2  0", "  4  3  0").replace("  1  2  1  0  0  0  0\n", "  1  2  1  0  0  0  0\n  1  4  2  0  0  0  0\n") \
    .replace("H   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2", "H   0  0  0  0  0  0  0  0  0  0  0  0\n    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2")


def ca(serial: int, chain: str, x: float) -> str:
    return f"ATOM  {serial:>5}  CA  ALA {chain}{serial:>4}    {x:>8.3f}{0.0:>8.3f}{0.0:>8.3f}  1.00  0.00           C"


class FallbackTest(unittest.TestCase):
    def test_sdf_matches_rust_layout(self):
        parts = fallback.sdf_parts(WATER)
        self.assertEqual([p["name"] for p in parts], ["bond", "bond", "atom_O", "atom_H", "atom_H"])
        self.assertEqual(parts[2]["color"], "#ff3b3b")

    def test_hostile_sdf_is_rejected(self):
        for bad in ("x\ny\nz\n999999  0 V2000\n", "x\ny\nz\n  3  2  0 V3000\n", WATER.replace("  1  3  1", "  1  9  1"),
                    WATER.replace("    0.2774", "       nan")):
            with self.assertRaises(ValueError):
                fallback.sdf_parts(bad)

    def test_pdb_chains_and_sampling(self):
        text = "\n".join([ca(i, "A", i * 3.8) for i in range(1, 5)] + [ca(i, "B", i * 3.8) for i in (5, 6)] + ["ENDMDL", ca(9, "C", 0)])
        parts = fallback.pdb_parts(text)
        self.assertEqual(sum(p["shape"] == "sphere" for p in parts), 6)
        self.assertEqual(sum(p["shape"] == "cylinder" for p in parts), 4)
        big = "\n".join(ca(i % 9999, "A", (i % 200) * 3.8) for i in range(1, 1001))
        balls = sum(p["shape"] == "sphere" for p in fallback.pdb_parts(big))
        self.assertTrue(fallback.MAX_RESIDUES // 2 <= balls <= fallback.MAX_RESIDUES)

    def test_chain_labels_are_localized(self):
        scene = {"title": "x", "parts": [{"name": "protein_chain_B", "label": "", "info": ""}, {"name": "atom_O", "label": "", "info": ""}]}
        out = exact.localize(scene, "it")
        self.assertEqual(out["parts"][0]["label"], "Catena B")
        self.assertEqual(out["parts"][1]["label"], "Ossigeno (O)")


class ResolveTest(unittest.TestCase):
    def setUp(self):
        resolve.CACHE.clear()

    def test_classify(self):
        self.assertEqual(resolve.classify("hemoglobin", {}), ("protein", "hemoglobin", True))
        self.assertEqual(resolve.classify("the caffeine molecule", {}), ("molecule", "caffeine", True))
        self.assertEqual(resolve.classify("heart", {}), ("molecule", "heart", False))
        self.assertEqual(resolve.classify("x", {"subject": "la proteína X", "protein": ["proteina"]})[0], "protein")

    def test_molecule_found_with_credit_and_progress(self):
        events = []
        with mock.patch.object(sources, "pubchem", new=mock.AsyncMock(return_value=(CAFFEINE_LIKE, "https://pubchem.ncbi.nlm.nih.gov/compound/962"))):
            scene = asyncio.run(resolve.find("caffeina", "caffeine", {}, lambda k, **p: events.append(k)))
        self.assertEqual(scene["credit"]["author"], "PubChem (NIH)")
        self.assertEqual(scene["title"], "caffeina")
        self.assertEqual(events, ["science_searching", "science_found"])

    def test_tiny_unasked_compounds_and_misses_are_ignored_and_cached(self):
        miss = mock.AsyncMock(side_effect=fetch.FetchError("holo_http_404"))
        with mock.patch.object(sources, "pubchem", new=miss):
            self.assertIsNone(asyncio.run(resolve.find("cuore", "heart", {})))
            self.assertIsNone(asyncio.run(resolve.find("cuore", "heart", {})))
        self.assertEqual(miss.await_count, 1)
        with mock.patch.object(sources, "pubchem", new=mock.AsyncMock(return_value=(WATER.replace("  3  2", "  2  1").replace("  1  3  1  0  0  0  0\n", ""), ""))):
            self.assertIsNone(asyncio.run(resolve.find("idrogeno", "hydrogen gas", {})))

    def test_transient_errors_are_not_cached(self):
        flaky = mock.AsyncMock(side_effect=fetch.FetchError("holo_http_503"))
        with mock.patch.object(sources, "pubchem", new=flaky):
            asyncio.run(resolve.find("acqua", "water", {}))
            asyncio.run(resolve.find("acqua", "water", {}))
        self.assertEqual(flaky.await_count, 2)

    def test_protein_alias_skips_search(self):
        text = "\n".join(ca(i, "A", i * 3.8) for i in range(1, 6))
        with mock.patch.object(sources, "rcsb", new=mock.AsyncMock(return_value=(text, "https://www.rcsb.org/structure/4HHB"))) as get, \
                mock.patch.object(sources, "rcsb_search", new=mock.AsyncMock()) as search:
            scene = asyncio.run(resolve.find("emoglobina", "hemoglobin", {}))
        get.assert_awaited_once_with("4HHB")
        search.assert_not_called()
        self.assertEqual(scene["credit"]["license"], "CC0 1.0")

    def test_sources_validate_names_before_network(self):
        for call in (sources.pubchem("../../etc"), sources.rcsb("../x"), sources.rcsb_search("<script>")):
            with self.assertRaises(fetch.FetchError):
                asyncio.run(call)


class NodeTest(unittest.TestCase):
    def test_only_private_network_addresses(self):
        self.assertEqual(node.validated("http://192.168.1.50:8081"), "http://192.168.1.50:8081")
        self.assertEqual(node.validated("http://127.0.0.1:8081"), "http://127.0.0.1:8081")
        for bad in ("http://169.254.169.254", "http://8.8.8.8:8081", "ftp://192.168.1.5", "http://user:pw@10.0.0.2", "http://10.0.0.2/?x=1"):
            with self.assertRaises(fetch.FetchError, msg=bad):
                node.validated(bad)

    def test_prompt_strips_markup(self):
        self.assertTrue(node.prompt("heart <script>").startswith("heart script"))


class ForgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalog = Catalog(Path(self.tmp.name))
        self.patches = [mock.patch.object(forge, "catalog", self.catalog), mock.patch.object(forge.state_store, "event")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def env(self, **values):
        return mock.patch.object(forge, "env_get", side_effect=lambda k, d="": values.get(k, d))

    def test_local_busy_falls_back_to_cloud_and_is_catalogued(self):
        events = []
        report = {"score": 80, "animations": 0, "triangles": 60000, "reasons": []}
        with self.env(), mock.patch.object(node, "url", return_value="http://10.0.0.5:8081"), \
                mock.patch.object(node, "generate", new=mock.AsyncMock(side_effect=node.NodeBusy("holo_gpu_busy"))), \
                mock.patch.object(meshy, "token", return_value="k"), \
                mock.patch.object(meshy, "generate", new=mock.AsyncMock(return_value=(b"glTF", "https://assets.meshy.ai/t.png"))), \
                mock.patch.object(judge, "inspect", return_value=report), \
                mock.patch.object(judge, "look", new=mock.AsyncMock(return_value={"match": 9, "quality": 8, "background": False})):
            entry = asyncio.run(forge.create("cuore", "cuore", "heart", lambda k, **p: events.append(k)))
        self.assertEqual(entry["license"], "forge_cloud")
        self.assertEqual(events, ["forge_local", "forge_local_busy", "forge_cloud", "forge_done"])
        self.assertIsNotNone(self.catalog.best("cuore"))

    def test_daily_cap_and_modes(self):
        with self.env(NUXIVA_HOLO_CLOUD_DAILY="1"):
            self.assertTrue(forge._take_cloud_slot())
            self.assertFalse(forge._take_cloud_slot())
        with self.env(NUXIVA_HOLO_GENERATE="off"), mock.patch.object(node, "generate", new=mock.AsyncMock()) as gen:
            self.assertIsNone(asyncio.run(forge.create("k", "x", "x")))
        gen.assert_not_called()
        with self.env(NUXIVA_HOLO_GENERATE="local"), mock.patch.object(node, "url", return_value=""), \
                mock.patch.object(meshy, "token", return_value="k"), mock.patch.object(meshy, "generate", new=mock.AsyncMock()) as cloud:
            self.assertIsNone(asyncio.run(forge.create("k", "x", "x")))
        cloud.assert_not_called()

    def test_wrong_generated_subject_is_rejected(self):
        with self.env(), mock.patch.object(node, "url", return_value=""), mock.patch.object(meshy, "token", return_value="k"), \
                mock.patch.object(meshy, "generate", new=mock.AsyncMock(return_value=(b"glTF", "https://assets.meshy.ai/t.png"))), \
                mock.patch.object(judge, "inspect", return_value={"score": 70, "animations": 0, "triangles": 1, "reasons": []}), \
                mock.patch.object(judge, "look", new=mock.AsyncMock(return_value={"match": 2, "quality": 9, "background": False})):
            self.assertIsNone(asyncio.run(forge.create("k", "cuore", "heart")))


class CascadeTest(unittest.TestCase):
    def tearDown(self):
        session.close()

    def test_science_wins_and_feeds_particles(self):
        sid = session.begin("caffeina", "realistic")
        scene = {"title": "caffeina", "euler": "XYZ", "layers": 1, "radius": 1, "parts": [
            {"name": "atom_O", "shape": "sphere", "half": [0.1, 0.1, 0.1], "at": [0, 0, 0], "rot": [0, 0, 0], "color": "#ff3b3b", "label": "", "info": ""}],
            "credit": {"name": "caffeine", "author": "PubChem (NIH)", "license": "Public domain", "page": ""}}
        with mock.patch.object(finder, "cached", return_value=None), mock.patch.object(finder, "english", new=mock.AsyncMock(return_value="caffeine")), \
                mock.patch.object(resolve, "find", new=mock.AsyncMock(return_value=scene)), \
                mock.patch.object(finder, "find", new=mock.AsyncMock()) as search, \
                mock.patch("agenti.hands.holo.commands.show_particles") as shown:
            asyncio.run(hd.build(sid, "caffeina", None, "it"))
        search.assert_not_called()
        shown.assert_called_once()
        snap = session.snapshot()
        self.assertEqual((snap["source"], snap["status"]), ("exact", "ready"))
        self.assertEqual(snap["scene"]["parts"][0]["label"], "Ossigeno (O)")

    def test_forge_runs_only_after_catalogue_misses(self):
        sid = session.begin("drago", "realistic")
        entry = {"id": "c" * 24, "name": "drago", "author": "Nuxiva", "license": "forge_local", "score": 72}
        with mock.patch.object(finder, "cached", return_value=None), mock.patch.object(finder, "english", new=mock.AsyncMock(return_value="dragon")), \
                mock.patch.object(resolve, "find", new=mock.AsyncMock(return_value=None)), \
                mock.patch.object(finder, "find", new=mock.AsyncMock(return_value=None)), \
                mock.patch.object(forge, "create", new=mock.AsyncMock(return_value=entry)) as made:
            asyncio.run(hd.build(sid, "drago", None, "it"))
        made.assert_awaited_once()
        self.assertEqual(session.snapshot()["scene"]["asset"]["license"], "forge_local")


if __name__ == "__main__":
    unittest.main()
