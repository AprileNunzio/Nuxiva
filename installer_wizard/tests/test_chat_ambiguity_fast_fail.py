import asyncio
import unittest
from unittest import mock

from features.actions import router as actions_router
from features.agent import commands as agent_cmd
from features.chat import assistant
from features.home_assistant.home import brain as home_brain
from features.understanding import router as understanding_router


class ChatAmbiguityFastFailTest(unittest.TestCase):
    def test_unrouted_ambiguous_request_fails_fast_without_calling_agent(self):
        called = {"agent": False, "core": False}

        async def fake_agent_answer(_text):
            called["agent"] = True
            return "Risposta agente", {"mode": "face"}

        async def fake_core_call(_text):
            called["core"] = True
            return {"speech_output": "Non ho la possibilità di comprendere questa richiesta.", "agent_id": "core_mock"}

        with mock.patch.object(understanding_router, "enabled", return_value=True), \
             mock.patch.object(understanding_router, "route", mock.AsyncMock(return_value=understanding_router.Decision())), \
             mock.patch.object(home_brain, "handle", mock.AsyncMock(return_value=None)), \
             mock.patch.object(agent_cmd, "answer", fake_agent_answer):
            result = asyncio.run(assistant.handle("a Cendilette Veletta", fake_core_call, {"lang": "it"}))

        self.assertFalse(called["agent"])
        self.assertTrue(called["core"])
        self.assertEqual(result["reply"], "Non ho capito la richiesta. Puoi ripetere?")
        self.assertEqual(result["ui"]["mode"], "face")

    def test_unrouted_request_does_not_call_agent_even_if_grounding_requests_lookup(self):
        called = {"agent": False, "core": False}

        async def fake_agent_answer(_text):
            called["agent"] = True
            return "Risposta agente", {"mode": "face"}

        async def fake_core_call(_text):
            called["core"] = True
            return {"speech_output": "Non capisco cosa intendi.", "agent_id": "core_mock"}

        with mock.patch.object(understanding_router, "enabled", return_value=True), \
             mock.patch.object(understanding_router, "route", mock.AsyncMock(return_value=understanding_router.Decision())), \
             mock.patch.object(home_brain, "handle", mock.AsyncMock(return_value=None)), \
             mock.patch("features.agent.grounding.needs_lookup", mock.AsyncMock(return_value=True)), \
             mock.patch.object(agent_cmd, "answer", fake_agent_answer):
            result = asyncio.run(assistant.handle("a Cendilette Veletta", fake_core_call, {"lang": "it"}))

        self.assertFalse(called["agent"])
        self.assertTrue(called["core"])
        self.assertEqual(result["reply"], "Non ho capito la richiesta. Puoi ripetere?")

    def test_unrouted_conversational_request_returns_model_answer_when_not_refused(self):
        called = {"agent": False, "core": False}

        async def fake_agent_answer(_text):
            called["agent"] = True
            return "Risposta agente", {"mode": "face"}

        async def fake_core_call(_text):
            called["core"] = True
            return {"speech_output": "Dante Alighieri è stato un sommo poeta fiorentino.", "agent_id": "core_mock"}

        with mock.patch.object(understanding_router, "enabled", return_value=True), \
             mock.patch.object(understanding_router, "route", mock.AsyncMock(return_value=understanding_router.Decision())), \
             mock.patch.object(home_brain, "handle", mock.AsyncMock(return_value=None)), \
             mock.patch.object(agent_cmd, "answer", fake_agent_answer):
            result = asyncio.run(assistant.handle("Chi era Dante Alighieri?", fake_core_call, {"lang": "it"}))

        self.assertFalse(called["agent"])
        self.assertTrue(called["core"])
        self.assertEqual(result["reply"], "Dante Alighieri è stato un sommo poeta fiorentino.")

    def test_explicit_weak_tool_command_is_not_treated_as_unrouted(self):
        called = {"agent": False, "core": False}

        async def fake_agent_answer(_text):
            called["agent"] = True
            return "Archivio compresso con successo.", {"mode": "face"}

        async def fake_core_call(_text):
            called["core"] = True
            return {"speech_output": "Non posso comprimere archivi.", "agent_id": "core_mock"}

        with mock.patch.object(understanding_router, "enabled", return_value=True), \
             mock.patch.object(understanding_router, "route", mock.AsyncMock(return_value=understanding_router.Decision())), \
             mock.patch.object(home_brain, "handle", mock.AsyncMock(return_value=None)), \
             mock.patch.object(actions_router, "handle", mock.AsyncMock(return_value=None)), \
             mock.patch.object(agent_cmd, "answer", fake_agent_answer):
            result = asyncio.run(assistant.handle("comprimi l'archivio documenti", fake_core_call, {"lang": "it"}))

        self.assertTrue(called["agent"])
        self.assertFalse(called["core"])
        self.assertEqual(result["reply"], "Archivio compresso con successo.")

    def test_empty_model_reply_on_unrouted_request_triggers_clarification(self):
        async def fake_core_call(_text):
            return {"speech_output": "   ", "agent_id": "core_mock"}

        with mock.patch.object(understanding_router, "enabled", return_value=True), \
             mock.patch.object(understanding_router, "route", mock.AsyncMock(return_value=understanding_router.Decision())), \
             mock.patch.object(home_brain, "handle", mock.AsyncMock(return_value=None)):
            result = asyncio.run(assistant.handle("a Cendilette Veletta", fake_core_call, {"lang": "it"}))

        self.assertEqual(result["reply"], "Non ho capito la richiesta. Puoi ripetere?")


if __name__ == "__main__":
    unittest.main()
