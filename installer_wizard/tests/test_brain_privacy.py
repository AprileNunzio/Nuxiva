import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sealed import SealedFile

from features.brain.privacy import origin
from features.brain.privacy.audit import BLOCKED, PrivacyAudit
from features.brain.privacy.detector import classify
from features.brain.privacy.gate import PrivacyBlocked, PrivacyGate
from features.brain.privacy.levels import PERSONAL, PUBLIC, SENSITIVE, strictest
from features.brain.privacy.policy import HOME, LOCAL, REMOTE, PolicyError, PolicyStore, parse, preset

ORIGINS = {"llama3:8b": LOCAL, "cloud:srv-casa/qwen": HOME, "cloud:openai/gpt-5": REMOTE}


class Index:
    def __init__(self, owner: str | None = "nunzio", names: tuple[str, ...] = ("martina",)) -> None:
        self._owner, self._names = owner, names

    def owner(self) -> str | None:
        return self._owner

    def names(self) -> tuple[str, ...]:
        return self._names


class PrivacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.local = True
        self.store = PolicyStore(SealedFile(root / "p.vault", root / "p.key"), lambda: self.local)
        self.audit = PrivacyAudit(SealedFile(root / "a.vault", root / "a.key"))
        self.present: list[str] = []
        self.gate = PrivacyGate(self.store, self.audit, ORIGINS.__getitem__, lambda: self.present, Index())
        self.models = list(ORIGINS)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_detector_levels(self):
        self.assertEqual(classify("che tempo fa domani a Roma?"), PUBLIC)
        self.assertEqual(classify("scrivi a mario.rossi@example.com"), PERSONAL)
        self.assertEqual(classify("chiama il 333 123 4567"), PERSONAL)
        self.assertEqual(classify("ho ritirato le analisi del sangue"), SENSITIVE)
        self.assertEqual(classify("il mio codice fiscale è RSSMRA80A01H501U"), SENSITIVE)
        self.assertEqual(classify("carta 4111 1111 1111 1111"), SENSITIVE)
        self.assertEqual(classify("ho consumato 1793000000 token"), PUBLIC)
        self.assertEqual(classify("domani Martina va a scuola", ("martina",)), PERSONAL)

    def test_strictest_level(self):
        self.assertEqual(strictest(PUBLIC, SENSITIVE, PERSONAL), SENSITIVE)
        self.assertEqual(strictest("bogus"), PUBLIC)

    def test_default_follows_local_engine(self):
        self.assertEqual(self.store.default().profile, "balanced")
        self.local = False
        self.assertEqual(self.store.default().profile, "open")

    def test_balanced_routes_by_level(self):
        self.assertEqual(self.gate.screen(self.models, PUBLIC), self.models)
        self.assertEqual(self.gate.screen(self.models, PERSONAL), ["llama3:8b", "cloud:srv-casa/qwen"])
        self.assertEqual(self.gate.screen(self.models, SENSITIVE), ["llama3:8b"])

    def test_sensitive_never_falls_back_to_cloud(self):
        with self.assertRaises(PrivacyBlocked):
            self.gate.screen(["cloud:openai/gpt-5"], SENSITIVE)
        self.assertEqual(self.audit.summary()["levels"][SENSITIVE][BLOCKED], 1)

    def test_open_profile_allows_everything(self):
        self.store.set_default({"profile": "open"})
        self.assertEqual(self.gate.screen(self.models, SENSITIVE), self.models)

    def test_person_policy_and_strictest_among_present(self):
        self.store.set_default({"profile": "open"})
        self.store.set_person("martina", {"profile": "max"})
        self.assertEqual(self.gate.screen(self.models, PERSONAL, "nunzio"), self.models)
        self.present = ["nunzio", "martina"]
        self.assertEqual(self.gate.screen(self.models, PERSONAL), ["llama3:8b"])
        self.store.set_person("martina", {"profile": "inherit"})
        self.assertEqual(self.gate.screen(self.models, PERSONAL), self.models)

    def test_custom_policy_validation(self):
        self.assertEqual(parse({"profile": "custom", "personal": "any", "sensitive": "home"}).sensitive, "home")
        for raw in ({"profile": "custom", "personal": "local", "sensitive": "any"}, {"profile": "x"}, [], {"profile": "custom"}):
            with self.assertRaises(PolicyError):
                parse(raw)
        with self.assertRaises(PolicyError):
            self.store.set_person("../etc", {"profile": "max"})

    def test_store_is_encrypted_and_reloaded(self):
        self.store.set_person("martina", {"profile": "max"})
        raw = (Path(self.dir.name) / "p.vault").read_bytes()
        self.assertNotIn(b"martina", raw)
        root = Path(self.dir.name)
        again = PolicyStore(SealedFile(root / "p.vault", root / "p.key"), lambda: False)
        self.assertEqual(again.own("martina"), preset("max"))

    def test_audit_counts_without_content(self):
        self.gate.served("cloud:openai/gpt-5", PUBLIC)
        self.gate.served("llama3:8b", SENSITIVE)
        summary = self.audit.summary()
        self.assertEqual(summary["levels"][PUBLIC][REMOTE], 1)
        self.assertEqual(summary["today"][SENSITIVE][LOCAL], 1)
        self.assertNotIn(b"gpt", (Path(self.dir.name) / "a.vault").read_bytes())

    def test_level_combines_sources(self):
        self.assertEqual(self.gate.level(("ciao",), component="mind"), PERSONAL)
        self.assertEqual(self.gate.level(("ciao",), declared=SENSITIVE), SENSITIVE)
        self.assertEqual(self.gate.level(("ciao",), personal=True), PERSONAL)
        self.assertEqual(self.gate.level(("ciao Martina",)), PERSONAL)

    def test_origin_of_engine_and_servers(self):
        with mock.patch.object(origin, "ollama_remote", return_value=False):
            self.assertEqual(origin.of("llama3:8b"), LOCAL)
        with mock.patch.object(origin, "ollama_remote", return_value=True), \
                mock.patch.object(origin, "ollama_url", return_value="http://192.168.1.20:11434"):
            self.assertEqual(origin.of("llama3:8b"), HOME)
        with mock.patch.object(origin, "ollama_remote", return_value=True), \
                mock.patch.object(origin, "ollama_url", return_value="https://ollama.example.com"):
            self.assertEqual(origin.of("llama3:8b"), REMOTE)
        self.assertEqual(origin.of("cloud:openai/gpt-5"), REMOTE)


if __name__ == "__main__":
    unittest.main()
