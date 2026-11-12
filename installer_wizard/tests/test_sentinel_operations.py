import json
import unittest
from unittest.mock import patch

from features.sentinel.collectors import operations
from features.sentinel import journey_detail


class OperationsTest(unittest.TestCase):
    def test_journey_detail_is_owner_only_and_redacts_credentials(self):
        from fastapi import HTTPException

        journey = {"id": "0123456789ab", "query": "Bearer example-secret", "answer": "ok",
                   "state": "done", "elapsed": 1, "nodes": []}
        with (patch.object(journey_detail, "require_permission"),
              patch.object(journey_detail, "account", return_value={"role": "auditor"}) as account,
              patch.object(journey_detail.journeys, "snapshot", return_value={"journeys": [journey]}),
              patch.object(journey_detail.record, "enabled", return_value=True),
              patch.object(journey_detail.record, "record") as audit):
            with self.assertRaises(HTTPException) as denied:
                journey_detail.detail(journey["id"], "reader")
            self.assertEqual(denied.exception.status_code, 403)
            account.return_value = {"role": "owner"}
            response = journey_detail.detail(journey["id"], "owner")
            self.assertEqual(json.loads(response.body)["answer"], "ok")
            self.assertNotIn(b"example-secret", response.body)
            audit.assert_called_once()

    @patch.object(operations.record, "record")
    def test_chat_correlates_the_journey_and_excludes_reply_text(self, record):
        operations.chat("admin", "journey-1", {
            "reply": "private transcript", "intent": "music", "verified": True,
            "execution_status": "completed", "ceo": {"planned_agent": "music", "reported_executor": "connector"},
        })
        kind, _, _, params = record.call_args.args
        self.assertEqual(kind, "self.chat_request")
        self.assertEqual(params["journey"], "journey-1")
        self.assertEqual((params["planned"], params["executor"]), ("music", "connector"))
        self.assertNotIn("private transcript", str(params))

    @patch.object(operations.record, "record")
    def test_unknown_mcp_method_is_not_retained(self, record):
        operations.mcp("unexpected-private-value", "", "failed", 12)
        self.assertEqual(record.call_args.args[3]["method"], "unknown")
