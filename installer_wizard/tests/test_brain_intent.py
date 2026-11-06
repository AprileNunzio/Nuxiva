import unittest
from unittest import mock

import brain_intent
import packages
from state import store


class BrainIntentTest(unittest.TestCase):
    def setUp(self):
        for target in (mock.patch.object(brain_intent, "ollama_remote", return_value=False),
                       mock.patch.object(packages, "ollama_remote", return_value=False),
                       mock.patch.object(packages, "DEMO", False)):
            target.start()
            self.addCleanup(target.stop)
        saved = dict(store.steps.get("ollama") or {})
        store.steps["ollama"] = {"status": "done"}
        self.addCleanup(lambda: store.steps.__setitem__("ollama", saved) if saved else store.steps.pop("ollama", None))

    def keyed(self, *pids):
        return mock.patch.object(brain_intent, "_keyed", side_effect=lambda pid: pid in pids)

    def test_a_cloud_key_without_ollama_moves_the_brain_to_the_cloud(self):
        with self.keyed("anthropic"), mock.patch.object(brain_intent, "local_engine", return_value=False):
            updates = brain_intent.reconcile({"NUXIVA_BRAIN": "local", "NUXIVA_LLM_CHAT_ORDER": "granite3.3:2b"})
        self.assertEqual(updates["NUXIVA_BRAIN"], "cloud")
        self.assertTrue(updates["NUXIVA_LLM_CHAT_ORDER"].startswith("cloud:anthropic/"))
        self.assertTrue(updates["NUXIVA_LLM_DEEP_ORDER"].startswith("cloud:anthropic/"))

    def test_cloud_orders_already_set_are_kept(self):
        env = {"NUXIVA_BRAIN": "pending", "NUXIVA_LLM_CHAT_ORDER": "cloud:gemini/gemini-3.8-flash"}
        with self.keyed("gemini"), mock.patch.object(brain_intent, "local_engine", return_value=True):
            self.assertEqual(brain_intent.reconcile(env), {"NUXIVA_BRAIN": "cloud"})

    def test_a_working_local_brain_is_left_alone(self):
        env = {"NUXIVA_BRAIN": "local", "NUXIVA_LLM_CHAT_ORDER": "granite3.3:8b"}
        with self.keyed("openai"), mock.patch.object(brain_intent, "local_engine", return_value=True):
            self.assertEqual(brain_intent.reconcile(env), {})

    def test_explicit_cloud_or_remote_choices_are_never_rewritten(self):
        with self.keyed("openai"), mock.patch.object(brain_intent, "local_engine", return_value=False):
            for mode in ("cloud", "remote"):
                self.assertEqual(brain_intent.reconcile({"NUXIVA_BRAIN": mode}), {}, mode)

    def test_no_key_no_change(self):
        with self.keyed(), mock.patch.object(brain_intent, "local_engine", return_value=False):
            self.assertEqual(brain_intent.reconcile({"NUXIVA_BRAIN": "local"}), {})

    def test_the_provider_in_the_chat_order_wins(self):
        env = {"NUXIVA_LLM_CHAT_ORDER": "cloud:mistral/mistral-small-latest"}
        with self.keyed("openai", "mistral"):
            self.assertEqual(brain_intent.cloud_provider(env), "mistral")

    def test_brain_mode_without_choice_follows_the_real_engine(self):
        with self.keyed("openai"), mock.patch.object(brain_intent, "local_engine", return_value=False):
            self.assertEqual(packages.brain_mode({}), "cloud")
        with self.keyed(), mock.patch.object(brain_intent, "local_engine", return_value=False):
            self.assertEqual(packages.brain_mode({}), "pending")
        with self.keyed("openai"), mock.patch.object(brain_intent, "local_engine", return_value=True):
            self.assertEqual(packages.brain_mode({}), "local")


if __name__ == "__main__":
    unittest.main()
