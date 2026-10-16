import unittest

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.chat.brain_chain import REASONING_PROFILES, cortical_chain


class ReasoningExplainTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.public)

    def test_profile_and_math_come_from_the_running_code(self):
        data = self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-6.0-pro"}).json()
        profile = {k: v for k, v in data["profile"].items() if k != "source"}
        self.assertEqual(profile, REASONING_PROFILES["nuxiva-6.0-pro"])
        self.assertEqual(data["routing"]["kind"], "deep")
        limbic = cortical_chain.limbic
        self.assertEqual(data["budget"]["result"], limbic.parallel_branch_budget(profile["parallel_branches"]))
        self.assertAlmostEqual(data["scoring"]["prune_below"], round(profile["ignition_threshold"] * 0.45, 3))

    def test_auto_lists_its_rules_with_real_profiles(self):
        data = self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-6.5-auto"}).json()
        self.assertEqual(data["profile"]["source"], "auto")
        self.assertEqual([r["profile"] for r in data["auto_rules"]],
                         ["nuxiva-5.0-fast", "nuxiva-5.0-empathetic", "nuxiva-6.5-ultra", "nuxiva-6.0-pro"])
        for rule in data["auto_rules"]:
            self.assertEqual(rule["params"], REASONING_PROFILES[rule["profile"]])

    def test_bad_and_unknown_modes(self):
        self.assertEqual(self.client.get("/api/assistant/mode/explain", params={"mode": "<x>"}).status_code, 400)
        self.assertEqual(self.client.get("/api/assistant/mode/explain", params={"mode": "nuxiva-9.9-nope"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
