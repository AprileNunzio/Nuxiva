"""
Test suite enterprise per la precisione di instradamento del CEO Executive e dello scanner agenti/widget.
Verifica la totale assenza di falsi positivi (0.001% tolleranza errori):
- Le richieste conversazionali e convenevoli ("ciao come va?", "chi sei?", "cosa puoi fare?")
  non devono MAI essere indirizzate a widget verticali (es. Lavagna).
- I comandi espliciti per la lavagna ("apri la lavagna", "disegna sulla lavagna")
  vengono assegnati correttamente alla Lavagna con massima confidenza.
- Le stopwords non innescano mai falsi punteggi su feature e widget.
"""

import unittest
from features.team.ceo import CEOExecutive
from features.team.stopwords import is_conversational_query, clean_tokens


class CEOExecutiveEnterpriseRoutingTest(unittest.TestCase):
    def setUp(self):
        self.ceo = CEOExecutive()

    def test_conversational_queries_are_detected(self):
        conversational_samples = [
            "ciao",
            "ciao come va?",
            "ciao come va",
            "come va?",
            "come stai?",
            "tutto bene?",
            "buongiorno",
            "buonasera",
            "salve",
            "chi sei?",
            "chi sei",
            "come ti chiami?",
            "cosa puoi fare?",
            "cosa sai fare?",
            "presentati",
            "raccontami di te",
            "hello",
            "how are you?",
            "what can you do?",
            "who are you?",
            "hola",
            "cómo estás?",
            "como estas",
            "qué tal?",
            "quién eres?",
            "qué puedes hacer?",
            "bonjour",
            "comment ça va?",
            "comment ca va",
            "qui es-tu?",
            "que peux-tu faire?",
            "hallo",
            "wie geht's?",
            "wie geht es dir?",
            "wer bist du?",
            "was kannst du tun?",
            "olá",
            "tudo bem?",
            "como vai?",
            "quem é você?"
        ]
        for query in conversational_samples:
            with self.subTest(query=query):
                self.assertTrue(
                    is_conversational_query(query),
                    f"La query '{query}' doveva essere riconosciuta come conversazionale generica"
                )

    def test_ciao_come_va_never_delegates_to_lavagna(self):
        decision = self.ceo.analyze_request("ciao come va?")
        self.assertNotEqual(decision.primary_agent.id, "whiteboard")
        self.assertNotEqual(decision.primary_agent.name, "Lavagna")
        self.assertIn(decision.primary_agent.id, ("chat", "agent", "understanding"))
        self.assertEqual(decision.confidence, 1.0)

    def test_identity_and_capability_questions_route_to_assistant(self):
        queries = [
            "chi sei?",
            "come ti chiami?",
            "cosa puoi fare?",
            "raccontami qualcosa",
            "come vanno le cose oggi?"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision = self.ceo.analyze_request(q)
                self.assertNotEqual(decision.primary_agent.id, "whiteboard")
                self.assertIn(decision.primary_agent.id, ("chat", "agent", "understanding"))

    def test_explicit_whiteboard_commands_route_to_whiteboard(self):
        whiteboard_queries = [
            "apri la lavagna",
            "apri la lavagna a tutto schermo",
            "scrivi alla lavagna",
            "disegna un diagramma sulla lavagna",
            "cancella la lavagna",
            "chiudi la lavagna"
        ]
        for q in whiteboard_queries:
            with self.subTest(query=q):
                decision = self.ceo.analyze_request(q)
                self.assertEqual(
                    decision.primary_agent.id,
                    "whiteboard",
                    f"La query esplicita per la lavagna '{q}' non è stata assegnata a whiteboard"
                )
                self.assertEqual(decision.primary_agent.name, "Lavagna")
                self.assertGreaterEqual(decision.confidence, 0.6)

    def test_explicit_camera_commands_route_to_cameras(self):
        decision = self.ceo.analyze_request("apri la telecamera")
        self.assertEqual(decision.primary_agent.id, "cameras")
        self.assertGreaterEqual(decision.confidence, 0.6)

    def test_explicit_music_commands_route_to_music(self):
        decision = self.ceo.analyze_request("metti un po' di musica")
        self.assertEqual(decision.primary_agent.id, "music")
        self.assertGreaterEqual(decision.confidence, 0.6)

    def test_stopwords_do_not_produce_tokens(self):
        stopwords_only = "come cosa fare per con da in su tra fra del della dello"
        tokens = clean_tokens(stopwords_only)
        self.assertEqual(tokens, set(), "Tutte le parole di test dovevano essere filtrate come stopwords")

    def test_synthesize_aligns_clean_agent_display(self):
        # 1. Caso conversazione generale: visualizza CEO [Assistente]
        decision = self.ceo.analyze_request("ciao come va?")
        raw_result = {
            "reply": "Signore, come va?",
            "intent": "conversation",
            "agent": "nuxiva_conversation · qwen2.5:1.5b (Nuxiva 6.0 Pro Omni-Latent)"
        }
        synthesized = self.ceo.synthesize(decision, raw_result)
        self.assertEqual(
            synthesized["agent"],
            "CEO [Assistente] · nuxiva_conversation · qwen2.5:1.5b (Nuxiva 6.0 Pro Omni-Latent)"
        )
        self.assertNotIn("Lavagna", synthesized["agent"])

        # 2. Caso comando verticale reale (es. lavagna): visualizza CEO [Lavagna]
        wb_decision = self.ceo.analyze_request("apri la lavagna a tutto schermo")
        wb_raw = {
            "reply": "Ecco la lavagna a tutto schermo.",
            "intent": "whiteboard",
            "agent": "whiteboard_controller"
        }
        wb_synthesized = self.ceo.synthesize(wb_decision, wb_raw)
        self.assertEqual(
            wb_synthesized["agent"],
            "CEO [Lavagna] · whiteboard_controller"
        )


if __name__ == "__main__":
    unittest.main()
