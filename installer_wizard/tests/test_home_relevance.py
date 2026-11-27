import asyncio
import unittest
from unittest import mock

import native_core

from agenti.home_assistant.nlu import resolver
from agenti.home_assistant.nlu.parser import judge, understand
from tests.test_home_resolve_native import catalog

READY = native_core.symbol("RustHomeResolver") is not None
CHATTER = (
    "Jarvis come va?",
    "ciao jarvis come va? tutto bene?",
    "come stai oggi",
    "che ore sono",
    "raccontami una barzelletta",
    "raccontami qualcosa sulla cucina italiana",
    "chi ha vinto la partita del Napoli?",
    "dimmi le notizie di oggi",
    "che tempo fa domani a Roma?",
    "how are you doing?",
    "what time is it?",
    "tell me a story",
    "¿qué tal estás?",
    "cuéntame un chiste",
    "comment ça va ?",
    "raconte-moi une histoire",
)
COMMANDS = (
    "accendi le luci della camera da letto",
    "Jarvis spegni la luce in cucina",
    "spegni la macchina del caffè",
    "abbassa la tapparella del soggiorno",
    "turn on the bedroom lights",
    "enciende las luces del dormitorio",
    "allume les lumières de la chambre",
)
SETTINGS = {"enabled": True, "url": "http://ha.local", "token": "t", "confirm": True}


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class RelevanceTests(unittest.TestCase):

    def setUp(self):
        self.cat = catalog()

    def test_conversation_is_not_for_the_home(self):
        for text in CHATTER:
            self.assertFalse(resolver.relevance(text, self.cat)["home"], text)
            self.assertIsNone(understand(text, self.cat), text)

    def test_home_commands_are_still_understood(self):
        for text in COMMANDS:
            judged = judge(text, self.cat)
            self.assertTrue(judged["home"], text)
            self.assertEqual(judged["purpose"], "command", text)
            self.assertEqual(understand(text, self.cat, judged=judged)["kind"], "command", text)

    def test_home_questions_are_still_understood(self):
        for text in ("le luci della cucina sono accese?", "com'è la temperatura in soggiorno?", "is the kitchen light on?"):
            self.assertTrue(judge(text, self.cat)["home"], text)

    def test_claim_is_zero_for_small_talk(self):
        from agenti.home_assistant.home import brain
        from agenti.understanding import claims, context
        with mock.patch.object(brain, "catalog", self.cat):
            for text in CHATTER:
                self.assertEqual(claims.home(context.build(text, None)), 0.0, text)


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class AssistGateTests(unittest.TestCase):

    def test_small_talk_never_reaches_assist(self):
        from agenti.home_assistant.home import brain
        assist = mock.AsyncMock(return_value={"ok": True, "speech": "Non trovo nessun dispositivo chiamato come"})
        with mock.patch.object(brain, "catalog", catalog()), \
                mock.patch.object(brain, "entities", {"light.cucina": {}}), \
                mock.patch.object(brain, "settings", return_value=SETTINGS), \
                mock.patch.object(brain, "status", "online"), \
                mock.patch.object(brain, "learned", {}), \
                mock.patch.object(brain, "pending", None), \
                mock.patch.object(brain, "ask_assist", assist):
            for text in CHATTER:
                self.assertIsNone(asyncio.run(brain.handle(text)), text)
        assist.assert_not_called()


class AssistAnswerTests(unittest.TestCase):

    def test_assist_errors_are_not_answers(self):
        from agenti.home_assistant.home import brain
        failure = {"response": {"response_type": "error", "data": {"code": "no_valid_targets"},
                                "speech": {"plain": {"speech": "Non trovo nessun dispositivo chiamato come"}}}}
        settings = dict(SETTINGS, url="", token="")
        with mock.patch.object(brain, "_ws", object()), \
                mock.patch.object(brain, "_call", mock.AsyncMock(return_value=failure)), \
                mock.patch.object(brain, "settings", return_value=settings):
            self.assertFalse(asyncio.run(brain.ask_assist("come va")).get("ok"))


if __name__ == "__main__":
    unittest.main()
