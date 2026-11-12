import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from features.brain import api, cervello_state
from features.brain.routing import assignment_service


class CervelloSyncTests(unittest.IsolatedAsyncioTestCase):
    async def synchronize(self, body):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(cervello_state, "STATE_DIR", Path(folder)), \
             patch.object(api, "write_env") as write, \
             patch.object(api.brains, "invalidate"), \
             patch("features.brain.free_router.settings.load", return_value={"enabled": True, "pools": ["chat"]}), \
             patch("features.brain.free_router.settings.save") as free_save, \
             patch.object(assignment_service, "assignments", return_value={"old": object()}), \
             patch.object(assignment_service, "save") as assignments, \
             patch.object(api, "unload_local_ollama_vram", new_callable=AsyncMock), \
             patch.dict(api.os.environ):
            result = await api.batch_save_brain_assignments(AsyncMock(json=AsyncMock(return_value=body)))
            saved = cervello_state.load()
            assignments.assert_called_once_with({"old": None})
            free_save.assert_called_once_with(False, ["chat"])
            return result, saved, write.call_args.args[0]

    async def test_cloud_reference_survives_reload(self):
        result, saved, env = await self.synchronize({
            "provider": "api_key", "serverId": "google", "modelName": "gemini-3.6-flash",
        })
        self.assertEqual(result["applied_model"], "cloud:gemini/gemini-3.6-flash")
        self.assertEqual(env["NUXIVA_BRAIN"], "cloud")
        self.assertEqual(saved["globalDefault"]["modelName"], result["applied_model"])
        self.assertEqual(env["NUXIVA_LLM_CHAT_ORDER"], result["applied_model"])

    async def test_remote_trailing_slash_does_not_duplicate_port(self):
        _, saved, env = await self.synchronize({
            "provider": "ollama_remote", "baseUrl": "http://172.17.89.73:11434/",
            "modelName": "richardyoung/lfm2.5-24b-a2b",
        })
        self.assertEqual(env["NUXIVA_OLLAMA_URL"], "http://172.17.89.73:11434")
        self.assertEqual(saved["globalDefault"]["baseUrl"], env["NUXIVA_OLLAMA_URL"])

    async def test_cloud_without_provider_is_rejected_before_writing(self):
        with patch.object(api, "write_env") as write:
            with self.assertRaises(api.HTTPException):
                await api.batch_save_brain_assignments(AsyncMock(json=AsyncMock(return_value={
                    "provider": "api_key", "modelName": "gemini-3.6-flash",
                })))
            write.assert_not_called()

    def test_empty_and_deleted_servers_remain_empty(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cervello_state, "STATE_DIR", Path(folder)):
            self.assertEqual(cervello_state.load()["servers"], [])
            cervello_state.save({"servers": [{"id": "mine"}]})
            self.assertEqual(cervello_state.load()["servers"], [{"id": "mine"}])
            cervello_state.save({"servers": []})
            self.assertEqual(cervello_state.load()["servers"], [])
