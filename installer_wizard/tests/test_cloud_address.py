import unittest

import httpx

from agenti.cloud.address import normalize
from agenti.cloud.catalog import BY_ID, RETIRED, make_ref, parse_ref
from agenti.cloud.failure import describe


class GroqAddressTests(unittest.TestCase):
    def test_groq_preset_is_the_openai_compatible_root(self):
        self.assertEqual(BY_ID["groq"].base_url, "https://api.groq.com/openai/v1")

    def test_user_entered_groq_addresses_are_repaired(self):
        for url in ("https://api.groq.com", "https://api.groq.com/v1", "https://api.groq.com/openai/v1/",
                    "https://api.groq.com/openai/v1/chat/completions", "https://api.groq.com/openai/v1/models"):
            self.assertEqual(normalize(url), "https://api.groq.com/openai/v1", url)

    def test_generic_addresses_keep_their_path_and_gain_a_version_only_when_missing(self):
        self.assertEqual(normalize("http://10.0.0.5:1234"), "http://10.0.0.5:1234/v1")
        self.assertEqual(normalize("https://nome.openai.azure.com/openai/v1/"), "https://nome.openai.azure.com/openai/v1")
        self.assertEqual(normalize("https://api.perplexity.ai/chat/completions"), "https://api.perplexity.ai")
        self.assertEqual(normalize(""), "")


class GroqModelTests(unittest.TestCase):
    def test_default_groq_models_are_not_retired(self):
        for model in BY_ID["groq"].models:
            self.assertNotIn(model, RETIRED["groq"])

    def test_retired_groq_models_move_to_their_replacement(self):
        self.assertEqual(parse_ref(make_ref("groq", "llama-3.3-70b-versatile")), ("groq", "openai/gpt-oss-120b"))
        self.assertEqual(parse_ref(make_ref("groq", "llama-3.1-8b-instant")), ("groq", "openai/gpt-oss-20b"))


class FailureTests(unittest.TestCase):
    def test_not_found_names_url_model_and_provider_message(self):
        res = httpx.Response(404, json={"error": {"message": "The model `x` does not exist", "code": "model_not_found"}})
        text = describe("Groq · x", "https://api.groq.com/openai/v1/chat/completions", res)
        self.assertIn("404", text)
        self.assertIn("https://api.groq.com/openai/v1/chat/completions", text)
        self.assertIn("does not exist", text)


if __name__ == "__main__":
    unittest.main()
