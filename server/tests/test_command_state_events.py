import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from server.core.agent_registry.interfaces import AgentTaskResponse
from server.features.mesh_coordinator.p2p_mesh import NuxivaMeshCoordinator
from server.features.mesh_coordinator.state_events import record_state_event


class StateEventsTest(unittest.TestCase):
    def test_command_metadata_is_persisted_without_user_content(self):
        event = {"event_type": "USER_COMMAND_EXECUTED", "task_id": "task-1", "agent": "home", "status": "SUCCESS"}
        with patch("server.core.event_sourcing.ledger.ledger.append_event") as append:
            NuxivaMeshCoordinator().commit_state_event(event)
        append.assert_called_once_with("task-1", "USER_COMMAND_EXECUTED", event)

    def test_undeclared_sensitive_fields_are_rejected(self):
        event = {"event_type": "USER_COMMAND_EXECUTED", "task_id": "task-1", "agent": "home", "status": "SUCCESS", "query": "private"}
        with self.assertRaises(ValidationError):
            record_state_event(event)


class CommandResponseTest(unittest.IsolatedAsyncioTestCase):
    async def execute(self, status="SUCCESS", persistence_error=None):
        from server.cmd import api_routes

        response = AgentTaskResponse(task_id="task-1", agent_id="home", status=status,
                                     speech_output="result", result_data={"verified": True}, execution_time_ms=1)
        with patch.object(api_routes.orchestrator_dispatcher, "dispatch_user_command", AsyncMock(return_value=response)) as dispatch, \
                patch.object(api_routes.p2p_mesh, "commit_state_event", side_effect=persistence_error) as persist:
            result = await api_routes.handle_user_command(api_routes.UserCommandPayload(query="command"))
        self.assertEqual(dispatch.await_count, 1)
        self.assertEqual(persist.call_count, 1)
        return result

    async def test_successful_command_returns_its_response(self):
        result = await self.execute()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["speech_output"], "result")
        self.assertTrue(result["state_event_recorded"])

    async def test_persistence_failure_does_not_repeat_an_executed_command(self):
        with self.assertLogs("nuxiva.commands", level="ERROR"):
            result = await self.execute(persistence_error=sqlite3.OperationalError("unavailable"))
        self.assertFalse(result["state_event_recorded"])
        self.assertEqual(result["speech_output"], "result")

    async def test_failed_execution_is_not_reported_as_successful(self):
        result = await self.execute(status="ERROR")
        self.assertEqual(result["status"], "error")
