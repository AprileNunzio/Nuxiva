import asyncio
import random
import unittest

import native_core

from agenti.chat import brain_chain
from agenti.team import router as team_router

TEXTS = ["ciao", "", "   ", "Errore di rete", "  ERRORE", "errore", "un errore qui", "\x1cerrore", "è tutto ok", "ERRORI"]
MODELS = [
    ["local-a", "local-b", "cloud:x", "cloud:y", "local-c"], ["cloud:x"], ["local-a"], [], ["cloud:a", "local-a", "cloud:b"],
]


def fake_is_cloud(name):
    return name.startswith("cloud:")


@unittest.skipIf(native_core.symbol("llm_cosine") is None, "modulo nativo assente")
class LlmParityTest(unittest.TestCase):
    def test_valid_matches_python(self):
        for text in TEXTS:
            with self.subTest(text=text):
                self.assertEqual(brain_chain.valid({"text": text}), brain_chain._py_valid(text))
        self.assertFalse(brain_chain.valid({}))

    def test_candidate_grouping_matches_python(self):
        original = brain_chain.is_cloud
        brain_chain.is_cloud = fake_is_cloud
        try:
            for models in MODELS:
                with self.subTest(models=models):
                    self.assertEqual(brain_chain._candidates(models), brain_chain._py_candidates(models))
        finally:
            brain_chain.is_cloud = original

    def test_score_matches_python(self):
        chain = brain_chain.CorticalBrainChain()

        class Plan:
            critic = True

        async def critic(candidate, limbic):
            return 0.5

        for confidence in (0.88, 0.35, 0.0, 1.0, 0.123456):
            candidate = {"confidence": confidence}
            got = asyncio.run(chain._score(candidate, Plan(), critic))
            want = round(confidence * brain_chain.CONFIDENCE_WEIGHT + 0.5 * brain_chain.CRITIC_WEIGHT, 3)
            self.assertEqual(round(got, 3), want)

    def test_cosine_and_ranking_match_python(self):
        rng = random.Random(7)
        engine = team_router.ToolRouter.__new__(team_router.ToolRouter)
        for _ in range(60):
            dim = rng.randint(1, 24)
            prompt = [rng.uniform(-1, 1) for _ in range(dim)]
            indexed = {f"agent{i}": [rng.uniform(-1, 1) for _ in range(dim)] for i in range(rng.randint(0, 20))}
            for other in indexed.values():
                self.assertAlmostEqual(engine.cosine_similarity(prompt, other), engine._py_cosine(prompt, other), places=12)
            engine.embeddings_cache = indexed
            for top_k in (0, 1, 3, 50):
                want = engine._py_retrieve(prompt, top_k)
                got = set(native_core.symbol("llm_retrieve")(prompt, list(indexed.items()), top_k, sorted(team_router.CORE_AGENTS)))
                self.assertEqual(got, want)

    def test_edge_inputs(self):
        engine = team_router.ToolRouter.__new__(team_router.ToolRouter)
        self.assertEqual(engine.cosine_similarity([], [1.0]), 0.0)
        self.assertEqual(engine.cosine_similarity([0.0, 0.0], [1.0, 2.0]), 0.0)
        self.assertEqual(engine.cosine_similarity([float("nan")], [1.0]).__class__, float)


class LlmFallbackTest(unittest.TestCase):
    def test_python_engine_stands_alone(self):
        self.assertTrue(brain_chain._py_valid("ciao"))
        self.assertFalse(brain_chain._py_valid("Errore"))


if __name__ == "__main__":
    unittest.main()
