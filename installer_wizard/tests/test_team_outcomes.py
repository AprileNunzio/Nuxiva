import unittest
from unittest import mock

from features.team.ceo import CEODecision, CEOExecutive
from features.team.outcomes import execution_outcome, messages
from features.team.scanner import DiscoveredAgent


class TeamOutcomeTest(unittest.TestCase):
    def test_success_requires_separate_evidence_to_be_verified(self):
        self.assertEqual(execution_outcome({"status": "SUCCESS"})["verification"], "unverified")
        self.assertEqual(execution_outcome({"status": "SUCCESS", "verified": True})["verification"], "verified")
        self.assertEqual(execution_outcome({"reply": "Completato con successo e verificato"})["status"], "unverified")

    def test_nested_failure_wins_over_outer_success(self):
        outcome = execution_outcome({"status": "success", "verified": True,
                                     "result_data": {"status": "FAILED", "error": "timeout"}})
        self.assertEqual(outcome["status"], "failed")
        self.assertFalse(outcome["verified"])

    def test_running_pending_and_blocked_are_preserved(self):
        for source, expected in (("STARTED_IN_BACKGROUND", "running"), ("awaiting_approval", "pending"),
                                 ("blocked", "blocked"), ("CANCELLED", "cancelled")):
            with self.subTest(source=source):
                outcome = execution_outcome({"result_data": {"status": source}})
                self.assertEqual(outcome["status"], expected)
                self.assertFalse(outcome["verified"])

    def test_verification_failure_and_cached_results_are_not_confirmed(self):
        for details in ({"verified": False}, {"verification": "unverified"}, {"cache_hit": True}):
            with self.subTest(details=details):
                outcome = execution_outcome({"status": "success", "verified": True, "result_data": details})
                self.assertFalse(outcome["verified"])

    def test_ceo_posts_only_the_structured_outcome_and_preserves_data(self):
        ceo = CEOExecutive()
        agent = DiscoveredAgent(id="agent", name="Assistente", description="Conversazione")
        decision = CEODecision(agent, [], "Rispondi", 0.8)
        cases = [({}, "unverified", "verifica"), ({"status": "failed"}, "failed", "errore"),
                 ({"status": "SUCCESS", "verified": True}, "completed", "conferma")]
        with mock.patch.object(ceo, "scan_team", return_value={"agent": agent}):
            for details, status, kind in cases:
                with self.subTest(details=details), mock.patch("features.team.ceo.board.post") as post:
                    raw = {"reply": "Tutto fatto", "intent": "conversation", "result_data": {"artifact": "file"}, **details}
                    result = ceo.synthesize(decision, raw)
                    self.assertEqual(result["outcome"]["status"], status)
                    self.assertEqual(result["ceo"]["outcome"], result["outcome"])
                    self.assertEqual(result["result_data"], {"artifact": "file"})
                    self.assertEqual(post.call_args.args[3], kind)
                    if kind != "conferma":
                        self.assertNotIn("successo", post.call_args.args[2])

    def test_outcome_localizations_have_matching_states(self):
        keys = set(messages("it"))
        for language in ("en", "fr", "es"):
            self.assertEqual(set(messages(language)), keys)


if __name__ == "__main__":
    unittest.main()
