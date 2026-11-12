import asyncio
import unittest

from features.cloud.catalog import BY_ID, make_ref, parse_ref
from features.cloud.tools import cloud_catalog


class CloudCatalogTests(unittest.TestCase):

    def test_gemini_models_include_3_8_flash_and_exclude_deprecated_2_5_flash(self):
        gemini = BY_ID["gemini"]
        self.assertIn("gemini-3.8-flash", gemini.models)
        self.assertIn("gemini-3.1-pro", gemini.models)
        self.assertNotIn("gemini-2.5-flash", gemini.models)

    def test_anthropic_models_include_claude_5_5(self):
        anthropic = BY_ID["anthropic"]
        self.assertIn("claude-sonnet-5-5", anthropic.models)
        self.assertIn("claude-haiku-5-5", anthropic.models)

    def test_openai_models_include_gpt_6_and_5_5(self):
        openai = BY_ID["openai"]
        self.assertIn("gpt-6-astra", openai.models)
        self.assertIn("gpt-6.1-sol", openai.models)
        self.assertIn("gpt-5.5", openai.models)

    def test_cloud_catalog_tool_returns_all_providers(self):
        data = asyncio.run(cloud_catalog())
        providers = data.get("providers", [])
        ids = {p["id"] for p in providers}
        self.assertIn("gemini", ids)
        self.assertIn("anthropic", ids)
        self.assertIn("openai", ids)

    def test_cloud_catalog_tool_filters_by_provider(self):
        data = asyncio.run(cloud_catalog("gemini"))
        providers = data.get("providers", [])
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]["id"], "gemini")
        self.assertIn("gemini-3.8-flash", providers[0]["models"])

    def test_parse_ref_and_make_ref(self):
        ref = make_ref("gemini", "gemini-3.8-flash")
        self.assertEqual(ref, "cloud:gemini/gemini-3.8-flash")
        p, m = parse_ref(ref)
        self.assertEqual((p, m), ("gemini", "gemini-3.8-flash"))


if __name__ == "__main__":
    unittest.main()
