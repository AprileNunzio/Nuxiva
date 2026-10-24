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


class FreshnessRoutingTest(unittest.TestCase):
    def test_time_sensitive_questions_go_to_tools_not_to_memory(self):
        from features.agent import commands
        for text in ("quando gioca il Napoli?", "ultime notizie sul terremoto", "quanto costa il bitcoin oggi", "chi è il presidente della Francia",
                     "che tempo farà domani", "com'è andata la partita", "chi è il miglior marcatore della NHL", "come sta andando Sinner nel ranking ATP",
                     "classifica del campionato di basket", "il Napoli ha infortunati"):
            with self.subTest(text=text):
                self.assertTrue(commands.fresh(text))
        for text in ("raccontami una barzelletta", "come si fa il tiramisù", "spiegami la fotosintesi"):
            with self.subTest(text=text):
                self.assertFalse(commands.fresh(text))


class PromiseDetectionTest(unittest.TestCase):
    def test_bare_promises_are_detected(self):
        from features.actions.router import promised
        self.assertTrue(promised("Subito, signore. Procedo…"))
        self.assertTrue(promised("Certo, procedo con lo scaricamento."))

    def test_real_answers_are_not_promises(self):
        from features.actions.router import promised
        self.assertFalse(promised("Il Napoli gioca domenica alle 18 contro la Roma."))
        self.assertFalse(promised("x" * 400))
