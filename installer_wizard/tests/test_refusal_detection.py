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
