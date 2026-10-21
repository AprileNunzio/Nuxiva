import unittest
from unittest.mock import AsyncMock, patch
from server.features.brain.service import BrainEngineService, normalize_ollama_host


class TestBrainResourceGovernor(unittest.TestCase):
    def test_normalize_ollama_host(self) -> None:
        self.assertEqual(normalize_ollama_host("192.168.1.50"), "http://192.168.1.50:11434")
        self.assertEqual(normalize_ollama_host("http://192.168.1.50:8080/"), "http://192.168.1.50:8080")
        self.assertEqual(normalize_ollama_host(""), "http://127.0.0.1:11434")
        self.assertEqual(normalize_ollama_host("https://ai.lan:11434"), "https://ai.lan:11434")

    async def _async_test_hibernation(self) -> None:
        service = BrainEngineService()
        res_active = await service.hibernate_local_ollama_if_unused(local_targets_count=2)
        self.assertFalse(res_active.hibernated)
        self.assertEqual(res_active.status, "active")
        self.assertEqual(res_active.active_local_targets, 2)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json = lambda: {"models": [{"name": "qwen2.5:7b"}]}
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value.status_code = 200
                res_hib = await service.hibernate_local_ollama_if_unused(local_targets_count=0)
                self.assertTrue(res_hib.hibernated)
                self.assertEqual(res_hib.status, "hibernated")
                self.assertEqual(res_hib.active_local_targets, 0)
                self.assertEqual(res_hib.reason_code, "resource.hibernate_zero_local_targets")

    def test_hibernation_logic(self) -> None:
        import asyncio
        asyncio.run(self._async_test_hibernation())


if __name__ == "__main__":
    unittest.main()
