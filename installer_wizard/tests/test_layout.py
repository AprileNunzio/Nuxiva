import unittest
from unittest.mock import AsyncMock, patch

from agenti.chat import code, layout, strict_reply

EXPLAIN = ("Una pagina HTML ha una testa con le informazioni per il browser e un corpo con ciò che si vede. "
           "Il tag meta charset dichiara la codifica dei caratteri, title dà il nome alla scheda. "
           "Nel corpo h1 è il titolo principale e p un paragrafo; il browser li dispone dall'alto in basso. "
           "Per aggiungere stile si usa un foglio CSS collegato nella testa.")
PAGE = "<!DOCTYPE html>\n<html>\n<head>\n  <meta charset=\"utf-8\">\n  <title>Prova</title>\n</head>\n<body>\n  <h1>Ciao</h1>\n</body>\n</html>"


class ChatOnlyTest(unittest.IsolatedAsyncioTestCase):
    async def test_calculation_is_in_the_reply_when_requested(self):
        from agenti.actions import calc

        with patch.object(calc, "llm", new_callable=AsyncMock, return_value={"expression": "120 * 0.85 / 3"}):
            reply, _ = await calc.calc_action("Quanti pezzi restano? Mostra il calcolo.")
        self.assertIn("Espressione: 120 * 0.85 / 3", reply)

    async def test_music_device_listing_uses_inventory_without_playback(self):
        from agenti.music import commands

        query = "Elenca i dispositivi disponibili per riprodurre musica. Non avviare la riproduzione."
        devices = [{"name": "Studio"}, {"name": "Cucina"}]
        with (patch.object(commands.outputs, "refresh", new_callable=AsyncMock, return_value=devices) as refresh,
              patch.object(commands.conf, "voice", return_value=True),
              patch.object(commands, "play", new_callable=AsyncMock) as play):
            self.assertTrue(commands.recognizes(query))
            reply, _ = await commands.answer(query)
            self.assertEqual(reply, "Dispositivi rilevati: Cucina, Studio")
            refresh.assert_awaited_once_with()
            play.assert_not_awaited()

    async def test_plans_do_not_enter_operational_routing(self):
        from agenti.chat import assistant

        core = AsyncMock()
        with patch.object(assistant, "generate", new_callable=AsyncMock, return_value="Piano") as model:
            for subject in ("un robot 3D", "un diorama", "un sito multilingua"):
                result = await assistant.handle(f"Progetta {subject} solo in chat. Non creare file.", core)
                self.assertEqual(result["reply"], "Piano")
                self.assertEqual(result["execution_status"], "not_executed")
                self.assertNotIn("files", result["ui"])
            self.assertEqual(model.await_count, 3)
            self.assertIsNone(model.await_args.kwargs["max_tokens"])
            self.assertIn("tolerances", model.await_args.kwargs["system"])
        core.assert_not_awaited()

    async def test_json_request_does_not_enter_operational_routing(self):
        from agenti.chat import assistant

        core = AsyncMock()
        with patch.object(assistant, "generate", new_callable=AsyncMock, side_effect=['{"ok": true}', "invalid"]):
            result = await assistant.handle("Estrai solo JSON: esempio", core)
            self.assertEqual(result["reply"], '{"ok": true}')
            result = await assistant.handle("Estrai solo JSON: esempio", core)
            self.assertEqual(result["error"], "invalid_json_reply")
        core.assert_not_awaited()


class LayoutTest(unittest.TestCase):
    def test_explicit_reply_formats(self):
        self.assertEqual(strict_reply.deterministic("Quanto fa 17 per 23? Rispondi solo con il numero."), "391")
        self.assertEqual(strict_reply.deterministic("Ordina alfabeticamente pera, mela, banana."),
                         "banana, mela, pera")
        self.assertIsNone(strict_reply.deterministic("Ordina alfabeticamente i file della cartella"))
        self.assertEqual(strict_reply.json_reply('```json\n{"importo": 125.50}\n```'), '{"importo": 125.5}')
        self.assertIsNone(strict_reply.json_reply('{"importo": NaN}'))

    def test_short_code_stays_in_widget(self):
        speech, ui = code.answer("Ecco la pagina, signore.\n```html\n" + PAGE + "\n```", "dammi il codice html")
        self.assertEqual(ui.pop("intent"), "code_view")
        self.assertEqual(ui["mode"], "face")
        self.assertNotIn("files", ui)
        self.assertEqual(layout.presence(speech, ui), "small")

    def test_explanation_and_code_side_by_side(self):
        speech, ui = code.answer(EXPLAIN + "\n```html\n" + PAGE + "\n```", "spiegami come si scrive una pagina html")
        self.assertEqual(ui.pop("intent"), "code_focus")
        self.assertEqual(ui["mode"], "focus")
        types = [p["type"] for p in ui["panels"]]
        self.assertEqual(types, ["text", "code"])
        self.assertEqual(sum(p["span"] for p in ui["panels"]), 12)
        self.assertLess(len(speech), 330)
        self.assertNotIn("<html>", speech)

    def test_code_first_when_asked_for_code(self):
        _, ui = code.answer(EXPLAIN + "\n```html\n" + PAGE + "\n```", "scrivimi una pagina html")
        self.assertEqual(ui["panels"][0]["type"], "code")

    def test_two_blocks_each_half(self):
        _, ui = code.answer(EXPLAIN + "\n```html\n" + PAGE + "\n```\n```css\nh1 { color: red; }\n```", "dammi html e css")
        codes = [p for p in ui["panels"] if p["type"] == "code"]
        self.assertEqual([p["span"] for p in codes], [6, 6])

    def test_presence_by_answer_size(self):
        self.assertEqual(layout.presence("Sono le 10 e 2, signore.", {"mode": "face"}), "large")
        self.assertEqual(layout.presence(" ".join(["parola"] * 40), {"mode": "face"}), "normal")
        speech, ui = layout.plan_text("Ecco.\n- il primo punto con molti dettagli\n- il secondo punto con altri dettagli\n"
                                      "- il terzo punto conclusivo", "elenca tre cose")
        self.assertEqual(ui["mode"], "focus")
        self.assertEqual([p["span"] for p in ui["panels"]], [5, 7])


if __name__ == "__main__":
    unittest.main()
