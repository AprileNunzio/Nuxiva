import unittest

from features.actions.router import REFUSAL


class RefusalDetectionTest(unittest.TestCase):
    def test_polite_lack_of_data_triggers_the_tool_agent(self):
        for reply in (
            "Signore, non dispongo dei dati in tempo reale sul calendario sportivo per poterle indicare la prossima partita del Napoli.",
            "Non ho accesso alle informazioni aggiornate.",
            "Non sono a conoscenza del risultato.",
            "Non posso farlo da qui.",
        ):
            with self.subTest(reply=reply):
                self.assertTrue(REFUSAL.search(reply))

    def test_ordinary_answers_are_not_refusals(self):
        for reply in ("Sono le 18:28 di giovedì.", "Il Napoli gioca sabato alle 20:45.", "Ho acceso la luce del salotto."):
            with self.subTest(reply=reply):
                self.assertIsNone(REFUSAL.search(reply))


if __name__ == "__main__":
    unittest.main()


class GroundingTest(unittest.IsolatedAsyncioTestCase):
    async def verdict(self, text, reply):
        from unittest import mock
        from features.agent import grounding
        grounding.cache.clear()
        calls = []

        async def fake(prompt, **kwargs):
            calls.append(prompt)
            if isinstance(reply, Exception):
                raise reply
            return reply

        with mock.patch.object(grounding, "generate", fake):
            return await grounding.needs_lookup(text), calls

    async def test_the_model_decides_without_keyword_lists(self):
        found, calls = await self.verdict("chi è il capocannoniere dell'hockey quest'anno?", {"lookup": True, "reason": "dato che cambia"})
        self.assertTrue(found)
        self.assertIn("capocannoniere", calls[0])
        self.assertFalse((await self.verdict("spiegami la fotosintesi", {"lookup": False, "reason": "conoscenza stabile"}))[0])

    async def test_verdicts_are_cached_and_failures_fall_back_to_the_model(self):
        from features.agent import grounding
        await self.verdict("quanto costa un bitcoin", {"lookup": True})
        self.assertIn("quanto costa un bitcoin", grounding.cache)
        from features.brain.llm import BrainUnavailable
        self.assertFalse((await self.verdict("altra domanda", BrainUnavailable("offline")))[0])
        self.assertFalse((await self.verdict("domanda strana", {"lookup": "forse"}))[0])


class PromiseDetectionTest(unittest.TestCase):
    def test_bare_promises_are_detected(self):
        from features.actions.router import promised
        self.assertTrue(promised("Subito, signore. Procedo…"))
        self.assertTrue(promised("Certo, procedo con lo scaricamento."))

    def test_real_answers_are_not_promises(self):
        from features.actions.router import promised
        self.assertFalse(promised("Il Napoli gioca domenica alle 18 contro la Roma."))
        self.assertFalse(promised("x" * 400))
