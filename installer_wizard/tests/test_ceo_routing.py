import unittest

from agenti.team import learning, relevance, routing
from agenti.team.ceo import CEOExecutive
from agenti.team.scanner import scanner

EVAL = [
    ("Mi mostri una medusa", "particles", "standard"),
    ("quanti battiti ho", "medico", "lampo"),
    ("com'è finito il Napoli", "sports", "standard"),
    ("creami un sito per la pizzeria", "devstudio", "progetto"),
    ("metti un po' di musica", "music", "standard"),
    ("ciao come stai", "chat", "lampo"),
    ("accendi la luce del salotto", "home_assistant", "standard"),
    ("che tempo fa domani", "weather", "lampo"),
    ("fammi vedere la telecamera del giardino", "cameras", "standard"),
    ("scrivi alla lavagna la formula di Einstein", "whiteboard", "lampo"),
]


class RoutingEvalTest(unittest.TestCase):
    def setUp(self):
        learning.reset()
        self.ceo = CEOExecutive()

    def test_eval_corpus_routes_and_levels(self):
        for text, agent, level in EVAL:
            with self.subTest(text=text):
                decision = self.ceo.analyze_request(text)
                self.assertEqual(decision.primary_agent.id, agent)
                self.assertEqual(decision.level, level)

    def test_python_engine_matches_the_corpus(self):
        router = routing.Router(native=False)
        agents = scanner.scan()
        for text, agent, level in EVAL:
            with self.subTest(text=text):
                routed = router.decide(agents, text, {})
                self.assertEqual(routed["primary"] or "chat", agent)
                self.assertEqual(routed["level"], level)

    def test_heavy_comes_from_the_manifest(self):
        agents = scanner.scan()
        heavy = {aid for aid, a in agents.items() if a.heavy}
        self.assertTrue({"particles", "vision", "models3d", "neural_radiance", "gaussian_splat", "depth_parallax"} <= heavy)
        self.assertEqual(self.ceo.analyze_request("che tempo fa domani").execution_tier, "balanced")
        self.assertEqual(self.ceo._resolve_node_delegation("x", False)[1], "balanced")

    def test_levels(self):
        base = {"project": False, "heavy": False, "risk": 0}
        self.assertEqual(routing.level(None, 0), "lampo")
        self.assertEqual(routing.level(base, 0), "lampo")
        self.assertEqual(routing.level(base, 1), "standard")
        self.assertEqual(routing.level({**base, "risk": 3}, 0), "standard")
        self.assertEqual(routing.level({**base, "heavy": True}, 0), "standard")
        self.assertEqual(routing.level({**base, "project": True}, 0), "progetto")

    def test_query_stems_are_deterministic(self):
        self.assertEqual(list(relevance.query_stems("salotti salotto luce")), ["luce", "salot"])
        self.assertEqual(relevance.query_stems("salotti salotto")["salot"], "salotto")

    def test_cards_are_complete(self):
        agents = scanner.scan()
        cards = routing.Router(native=False).cards(agents)
        self.assertEqual(set(cards), set(agents))
        medico = cards["medico"]
        self.assertGreaterEqual(medico["risk"], 2)
        self.assertTrue(cards["devstudio"]["project"])
        self.assertIn("medusa", " ".join(cards["particles"]["nouns"]).lower())

    def test_long_queries_are_clipped(self):
        decision = self.ceo.analyze_request("medusa " * 5000)
        self.assertEqual(decision.primary_agent.id, "particles")


if __name__ == "__main__":
    unittest.main()
