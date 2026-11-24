import unittest
from unittest import mock

from fastapi import HTTPException

from agenti.reason_lab import brain_default


def patched(main, entry=None, configured=True):
    return [
        mock.patch.object(brain_default.brains, "config", return_value={"main": main, "fast": "small:1b"}),
        mock.patch.object(brain_default, "ollama_url", return_value="http://127.0.0.1:11434/"),
        mock.patch.object(brain_default.vault, "get", return_value=entry or {}),
        mock.patch.object(brain_default.vault, "configured", return_value=configured),
    ]


class BrainDefaultTests(unittest.TestCase):
    def resolve(self, main, entry=None, configured=True, role="main"):
        patches = patched(main, entry, configured)
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return brain_default.resolve(role)

    def test_a_local_model_uses_the_configured_ollama_address(self):
        resolved = self.resolve("granite3.3:2b")
        self.assertEqual((resolved["backend"], resolved["base_url"], resolved["key"], resolved["supported"]),
                         ("ollama", "http://127.0.0.1:11434", None, True))

    def test_the_fast_role_can_be_chosen(self):
        self.assertEqual(self.resolve("granite3.3:2b", role="fast")["model"], "small:1b")

    def test_a_cloud_provider_takes_its_key_from_the_vault(self):
        resolved = self.resolve("cloud:openai/gpt-5.5", {"key": "k" * 20})
        self.assertEqual((resolved["backend"], resolved["base_url"], resolved["model"], resolved["key"], resolved["supported"]),
                         ("openai", "https://api.openai.com/v1", "gpt-5.5", "k" * 20, True))

    def test_a_provider_without_a_compatible_api_is_marked_unsupported(self):
        self.assertFalse(self.resolve("cloud:anthropic/claude-sonnet-5-5", {"key": "k" * 20})["supported"])

    def test_a_provider_that_is_not_configured_is_marked_unsupported(self):
        self.assertFalse(self.resolve("cloud:openai/gpt-5.5", {}, configured=False)["supported"])

    def test_an_unknown_role_is_refused(self):
        with self.assertRaises(HTTPException):
            brain_default.resolve("deep")

    def test_the_public_view_never_contains_the_key(self):
        for patch in patched("cloud:openai/gpt-5.5", {"key": "k" * 20}):
            patch.start()
            self.addCleanup(patch.stop)
        view = brain_default.public()
        self.assertTrue(view["has_key"])
        self.assertNotIn("key", view)
        self.assertNotIn("k" * 20, str(view))


if __name__ == "__main__":
    unittest.main()
