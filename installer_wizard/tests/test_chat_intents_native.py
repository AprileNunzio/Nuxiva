import unittest

import native_core

from agenti.chat import intents

CORPUS = [
    "che tempo fa domani", "pioverà a Milano?", "serve l'ombrello", "Com'è il tempo oggi", "forecast for tomorrow",
    "chi canta questa canzone", "che musica è", "cosa sto ascoltando", "cosa stai studiando", "come vanno gli studi",
    "mostrami la memoria", "cosa ricordi", "stato del sistema", "diagnostica", "accendi la webcam", "spegni la fotocamera",
    "chi vedi", "mi riconosci", "scansiona la rete", "chi è connesso", "abito a Roma", "dove siamo", "quanti anni ho",
    "mio compleanno", "appunta che ho 42 anni", "mi chiamo Luca", "chiamami Gigi", "che voci hai", "scarica la voce inglese",
    "which languages can you", "è passato il corriere", "chi c'era al cancello", "stato di soccorso", "ci sono emergenze",
    "dispositivi matter", "che ore sono", "che giorno è", "raccontami una storia", "", "   ", "accendi la luce in cucina",
    "METEO", "CHE ORE SONO", "Che Tempo Fa", "mostra la webcam. e poi", "àèìòù", "tempo di cottura", "meteorite",
    "ho ٣ anni", "\u0000meteo", "meteo\u0000", "x" * 5000, "È la mia ETÀ ?", "qual è la mia età", "ŞİŁ meteo",
]


@unittest.skipIf(native_core.symbol("RustIntents") is None, "modulo nativo assente")
class ChatIntentsParityTest(unittest.TestCase):
    def test_corpus_matches_python_engine(self):
        engine = native_core.symbol("RustIntents")()
        for text in CORPUS:
            with self.subTest(text=text[:60]):
                self.assertEqual(engine.detect(text), intents._py_detect_intent(text))

    def test_table_names_match(self):
        engine = native_core.symbol("RustIntents")()
        self.assertEqual(engine.names(), [name for name, _ in intents.INTENTS])

    def test_delegate_uses_native(self):
        self.assertEqual(intents.detect_intent("che ore sono"), "time")
        self.assertEqual(intents.detect_intent("boh"), "conversation")


class ChatIntentsFallbackTest(unittest.TestCase):
    def test_python_engine_stands_alone(self):
        self.assertEqual(intents._py_detect_intent("che tempo fa"), "weather")
        self.assertEqual(intents._py_detect_intent("niente"), "conversation")


if __name__ == "__main__":
    unittest.main()
