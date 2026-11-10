import unittest
from unittest.mock import patch

from features.sentinel.ask import AskCore


class FakeRustAskCore:

    def parse(self, text, now_ms):
        import json
        if "corriere" in text or "courier" in text:
            return json.dumps({
                "lang": "it",
                "kind": "when",
                "from_ms": now_ms - 86400000 * 2,
                "to_ms": now_ms - 86400000,
                "target_role": "courier",
                "class": "person",
                "upper_color": None,
                "lower_color": None,
                "headwear": None,
                "item": None,
                "vehicle_kind": None,
                "vehicle_color": None,
                "camera_or_zone": None,
            })
        return json.dumps({
            "lang": "en",
            "kind": "what_look",
            "from_ms": now_ms - 86400000,
            "to_ms": now_ms,
            "target_role": None,
            "class": "person",
            "upper_color": "red",
            "lower_color": None,
            "headwear": None,
            "item": None,
            "vehicle_kind": None,
            "vehicle_color": None,
            "camera_or_zone": None,
        })

    def evaluate(self, query_json, sightings_json):
        import json
        q = json.loads(query_json)
        sightings = json.loads(sightings_json)
        if not sightings:
            return json.dumps({
                "found": False,
                "summary": "Nessuna prova sufficiente trovata per l'intervallo richiesto.",
                "citations": [],
                "scanned": 0,
                "matched_count": 0,
            })
        s = sightings[0]
        citation = {
            "sighting_id": s["id"],
            "timestamp_ms": s["start_ms"],
            "time_str": "14:22",
            "camera": s["camera"],
            "zone": s.get("zone"),
            "class": s["class"],
            "who": s["who"],
            "appearance_desc": "sopra red, parcel",
            "frame_evidence_id": "frame_1",
            "clip_evidence_id": "clip_1",
            "confidence_pct": 92,
        }
        return json.dumps({
            "found": True,
            "summary": "Il corriere è stato rilevato alle ore 14:22 su telecamera 'cancello'. Prove: fotogramma #frame_1.",
            "citations": [citation],
            "scanned": len(sightings),
            "matched_count": 1,
        })


class TestSentinelAsk(unittest.TestCase):

    def setUp(self):
        self.clock = 1700000000.0
        self.asker = AskCore(clock=lambda: self.clock)
        self.asker._engine = FakeRustAskCore()

    @patch("features.sentinel.memory.memory.search")
    @patch("features.sentinel.record.record")
    def test_ask_courier_found(self, mock_record, mock_search):
        mock_search.return_value = {
            "sightings": [{
                "id": "s_100",
                "start_ms": 1699913600000,
                "end_ms": 1699913660000,
                "camera": "cancello",
                "zone": "ingresso",
                "class": "person",
                "who": {"type": "unknown"},
                "look": {"upper": "red", "carrying": ["parcel"]},
                "confidence": 0.92,
            }]
        }

        ans = self.asker.ask("a che ora è venuto il corriere ieri e com'era vestito?", user="admin")
        self.assertTrue(ans["found"])
        self.assertEqual(len(ans["citations"]), 1)
        self.assertEqual(ans["citations"][0]["camera"], "cancello")
        self.assertIn("14:22", ans["summary"])
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0], "sentinel.read")
        self.assertEqual(args[2], "sentinel.sentinel.ask_query")
        self.assertEqual(args[3]["citations"], 1)

    @patch("features.sentinel.memory.memory.search")
    @patch("features.sentinel.record.record")
    def test_ask_not_found(self, mock_record, mock_search):
        mock_search.return_value = {"sightings": []}

        ans = self.asker.ask("chi è passato stamattina?", user="admin")
        self.assertFalse(ans["found"])
        self.assertEqual(len(ans["citations"]), 0)
        mock_record.assert_called_once()
        self.assertEqual(mock_record.call_args[0][3]["citations"], 0)


if __name__ == "__main__":
    unittest.main()
