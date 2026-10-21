import os
import unittest
from unittest.mock import Mock, patch

class TestNodeCapabilities(unittest.TestCase):
    def setUp(self):
        os.environ.pop("NUXIVA_LOCAL_OLLAMA_DISABLED", None)
        runner = patch("node_api.subprocess.run")
        runner.start()
        self.addCleanup(runner.stop)

    def test_capabilities_load_defaults(self):
        from node_api import _load_capabilities, is_capability_enabled
        caps = _load_capabilities("test_node")
        self.assertTrue(caps.get("brain_llm"))
        self.assertTrue(is_capability_enabled("brain_llm", "test_node"))

    def test_toggle_capability_disables_ollama(self):
        from node_api import toggle_node_capability, ToggleCapabilityRequest, is_capability_enabled
        req = ToggleCapabilityRequest(capability="brain_llm", enabled=False)
        with patch("psutil.process_iter", return_value=[]):
            res = toggle_node_capability("test_node", req)
        self.assertFalse(res["capabilities"]["brain_llm"])
        self.assertFalse(is_capability_enabled("brain_llm", "test_node"))
        self.assertEqual(os.environ.get("NUXIVA_LOCAL_OLLAMA_DISABLED"), "1")

        req_re_enable = ToggleCapabilityRequest(capability="brain_llm", enabled=True)
        res_re = toggle_node_capability("test_node", req_re_enable)
        self.assertTrue(res_re["capabilities"]["brain_llm"])
        self.assertTrue(is_capability_enabled("brain_llm", "test_node"))
        self.assertIsNone(os.environ.get("NUXIVA_LOCAL_OLLAMA_DISABLED"))

    def test_disabled_capability_survives_missing_env_flag_and_is_enforced(self):
        import node_api

        with patch.object(node_api, "is_capability_enabled", return_value=False):
            os.environ.pop("NUXIVA_LOCAL_OLLAMA_DISABLED", None)
            self.assertTrue(node_api.local_ollama_disabled())
            running = [object()]
            with patch.object(node_api, "_local_llm_processes", return_value=running), \
                 patch.object(node_api, "stop_local_ollama") as stop, \
                 patch.object(node_api, "_sync_local_llm_marker") as marker:
                self.assertTrue(node_api.enforce_local_ollama_off())
            stop.assert_called_once()
            marker.assert_called_once_with(True)
            with patch.object(node_api, "_local_llm_processes", return_value=[]), \
                 patch.object(node_api, "stop_local_ollama") as stop:
                self.assertFalse(node_api.enforce_local_ollama_off())
            stop.assert_not_called()
        os.environ.pop("NUXIVA_LOCAL_OLLAMA_DISABLED", None)

    def test_install_steps_do_not_restart_local_ollama_when_disabled(self):
        import asyncio
        import node_api
        import steps

        step = next(s for s in steps.STEPS if s.id == "ollama")
        with patch.object(node_api, "local_ollama_disabled", return_value=True):
            self.assertEqual(asyncio.run(steps.run_step_action(step, "apply")), (0, ""))
        with patch.object(node_api, "local_ollama_disabled", return_value=False):
            self.assertFalse(steps._local_llm_step_skipped(step))

    def test_process_matching_ignores_commands_that_only_mention_ollama(self):
        import node_api
        processes = [
            Mock(pid=901, info={"name": "ollama", "cmdline": ["/usr/local/bin/ollama", "serve"]}),
            Mock(pid=902, info={"name": "llama-server", "cmdline": ["/usr/lib/ollama/llama-server"]}),
            Mock(pid=903, info={"name": "python", "cmdline": ["python", "-c", "check_ollama()"]}),
            Mock(pid=904, info={"name": "bash", "cmdline": ["bash", "50-ollama.sh"]}),
        ]
        with patch("psutil.process_iter", return_value=processes):
            self.assertEqual(node_api._local_llm_processes(), processes[:2])
if __name__ == "__main__":
    unittest.main()
