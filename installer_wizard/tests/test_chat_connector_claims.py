import sys
import types
import unittest
from unittest import mock

from features.agent import registry
from features.agent import tools_comm  # noqa: F401
from features.chat import assistant
from features.chat.claims import ConnectorClaims
from features.google import commands as google

GOOGLE_PHRASES = {
    "scarica le bollette di Octopus dalla mail nella cartella bollette": "mail_download",
    "scarica le bollette di Octopus dalla gmail": "mail_download",
    "cerca le mail di Octopus": "mail",
    "cerca le email di Octopus": "mail",
    "ho email non lette?": "mail",
    "leggi l'ultima email": "mail_read",
    "prossimi appuntamenti": "calendar",
    "che appuntamenti ho domani": "calendar",
}
NOT_GOOGLE = ["accendi la luce della cucina", "qual è la capitale della Francia", "suona un po' di musica", "apri la lavagna"]


class MatchTest(unittest.TestCase):
    def test_reported_phrases_reach_the_expected_google_command(self):
        for phrase, command in GOOGLE_PHRASES.items():
            self.assertEqual((phrase, (google.match(phrase) or ("",))[0]), (phrase, command))
            self.assertTrue(google.recognizes(phrase), phrase)

    def test_an_email_address_lookup_is_still_a_contact_request(self):
        for phrase in ("dammi l'indirizzo email di Mario Rossi", "qual è l'email di Mario Rossi"):
            self.assertNotEqual((google.match(phrase) or ("",))[0], "mail", phrase)

    def test_unrelated_requests_are_not_claimed(self):
        for phrase in NOT_GOOGLE:
            self.assertFalse(google.recognizes(phrase), phrase)


class ClaimsTest(unittest.TestCase):
    def setUp(self):
        self.modules = {}
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in self.modules])

    def module(self, name: str, **attributes) -> str:
        mod = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(mod, key, value)
        sys.modules[name] = mod
        self.modules[name] = mod
        return name

    def test_only_connectors_that_declare_a_claim_are_asked_and_in_registration_order(self):
        claims = ConnectorClaims({
            "one": self.module("claims_one", recognizes=lambda t: "uno" in t),
            "silent": self.module("claims_silent"),
            "two": self.module("claims_two", recognizes=lambda t: "uno" in t or "due" in t),
        })
        self.assertEqual(claims.claiming("uno"), ["one", "two"])
        self.assertEqual(claims.claiming("due"), ["two"])
        self.assertEqual(claims.claiming("tre"), [])

    def test_broken_connectors_are_reported_and_never_block_the_others(self):
        def explode(_):
            raise RuntimeError("boom")

        claims = ConnectorClaims({
            "missing": "claims_does_not_exist",
            "bad": self.module("claims_bad", recognizes=explode),
            "good": self.module("claims_good", recognizes=lambda t: True),
        })
        with mock.patch("features.chat.claims.store.event") as event:
            self.assertEqual(claims.claiming("x"), ["good"])
        self.assertEqual(event.call_count, 2)
        self.assertTrue(all(call.args[0] == "WARN" for call in event.call_args_list))


class RoutingTest(unittest.IsolatedAsyncioTestCase):
    async def route(self, text: str, claimed: list[str], connect_result, refused=None):
        stub = mock.Mock(claiming=mock.Mock(return_value=claimed))
        connect = mock.AsyncMock(return_value=connect_result)
        strong = mock.Mock(side_effect=AssertionError("l'agente generico non deve essere interpellato"))
        with mock.patch.object(assistant, "CLAIMS", stub), mock.patch.object(assistant, "_connect", connect), \
                mock.patch.object(assistant, "_refused", return_value=refused), \
                mock.patch("features.agent.commands.strong", strong):
            return await assistant._route(text, mock.AsyncMock(), None), connect

    async def test_a_claiming_connector_answers_before_the_generic_agent_and_the_classifier(self):
        expected = {"reply": "ok", "ui": {}, "intent": "gservices", "agent": "gservices", "elapsed_ms": 1}
        out, connect = await self.route("scarica le bollette di Octopus dalla mail", ["gservices"], expected)
        self.assertEqual(out, expected)
        self.assertEqual(connect.call_args.args[2], ("gservices",))

    async def test_a_refused_connector_explains_the_reason_instead_of_falling_through(self):
        refusal = {"reply": "motivo", "ui": {}, "intent": "authz", "agent": "autorizzazioni", "elapsed_ms": 1}
        out, connect = await self.route("che appuntamenti ho domani", ["gservices"], None, refused=refusal)
        self.assertEqual(out, refusal)
        connect.assert_not_called()


class IntentGuardTest(unittest.TestCase):
    def ask(self, request: str) -> str:
        token = registry.REQUEST.set(request)
        try:
            return registry.unrequested("send_email")
        finally:
            registry.REQUEST.reset(token)

    def test_sending_an_email_requires_an_explicit_request(self):
        for request in ("scarica le bollette di Octopus dalla mail nella cartella bollette", "leggi l'ultima email", ""):
            self.assertIn("richiede una richiesta esplicita", self.ask(request), request)

    def test_explicit_requests_are_allowed(self):
        for request in ("invia una mail a Mario", "mandami le bollette via email", "inoltra il messaggio a Luca", "rispondi a Anna"):
            self.assertEqual(self.ask(request), "", request)

    def test_tools_without_a_declared_intent_are_unaffected(self):
        self.assertEqual(registry.unrequested("share_folder"), "")


if __name__ == "__main__":
    unittest.main()
