import unittest
from unittest import mock

import httpx

import llm_probe


class JudgeTest(unittest.TestCase):

    def test_a_model_out_of_memory_is_fine_when_it_is_only_a_fallback(self):
        out = llm_probe.judge("qwen2.5:7b", [], ["qwen2.5:7b"], resident=False)
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["on_demand"])

    def test_a_first_choice_model_out_of_memory_is_warmed(self):
        self.assertEqual(llm_probe.judge("qwen2.5:7b", [], ["qwen2.5:7b"], resident=True)["status"], "warn")

    def test_a_missing_model_is_a_real_problem_and_a_loaded_one_is_ok(self):
        self.assertIn("non installato", llm_probe.judge("qwen2.5:7b", [], ["llama3:8b"], resident=False)["detail"])
        self.assertEqual(llm_probe.judge("qwen2.5:7b", ["qwen2.5:7b"], ["qwen2.5:7b"], resident=False)["status"], "ok")


class ProbeTest(unittest.IsolatedAsyncioTestCase):

    async def run_probe(self, handler, resident=False):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with mock.patch.object(llm_probe, "resident_first", lambda: resident):
                return await llm_probe.probe(client, "http://ollama", "qwen2.5:7b")

    async def test_installed_but_idle_model_is_not_reported(self):
        def handler(request):
            models = [] if request.url.path == "/api/ps" else [{"name": "qwen2.5:7b"}]
            return httpx.Response(200, json={"models": models})
        self.assertEqual((await self.run_probe(handler))["status"], "ok")

    async def test_unreachable_ollama_is_down(self):
        def handler(request):
            return httpx.Response(500)
        self.assertEqual((await self.run_probe(handler))["status"], "down")


if __name__ == "__main__":
    unittest.main()
