import unittest

from features.brain.assignments import Assignment
from features.brain.everywhere import EverywhereError, assignment_updates, clean_model, role_updates
from features.brain.roles import ROLES
from features.brain.tuning import Tuning

HEADERS = {"X-Nuxiva-Request": "1"}
MODEL = "cloud:pc_studio/qwen3:14b"


class EverywherePlanTests(unittest.TestCase):
    def test_rejects_unsafe_model_refs(self):
        for bad in ("", " ", "../etc", "a b", "x" * 200, None, "cloud:x/<script>"):
            with self.assertRaises(EverywhereError):
                clean_model(bad)
        self.assertEqual(clean_model(f"  {MODEL} "), MODEL)

    def test_only_mode_puts_single_model_on_every_role(self):
        updates = role_updates(MODEL, {"chat": ["a", "b"]}, keep=False)
        for role in ROLES:
            self.assertEqual(updates[role.env_key], MODEL)
            self.assertEqual(updates[role.profile_key], "custom")
            self.assertEqual(updates[role.scope_key], "")
            self.assertEqual(updates[role.strategy_key], "")

    def test_keep_mode_prepends_and_dedupes_backups(self):
        updates = role_updates(MODEL, {"chat": ["a", MODEL, "b"]}, keep=True)
        self.assertEqual(updates["NUXIVA_LLM_CHAT_ORDER"], f"{MODEL},a,b")
        long_chain = {"deep": [f"m{i}" for i in range(20)]}
        self.assertEqual(len(role_updates(MODEL, long_chain, keep=True)["NUXIVA_LLM_DEEP_ORDER"].split(",")), 12)

    def test_assignments_follow_the_model_and_keep_tuning(self):
        tuning = Tuning()
        current = {
            "agency_director": Assignment("deep", ("x", "y"), "first", tuning),
            "agency_critic": Assignment("deep", (), "inherit", tuning),
        }
        only = assignment_updates(MODEL, current, keep=False)
        self.assertEqual(set(only), {"agency_director"})
        self.assertEqual(only["agency_director"].order, (MODEL,))
        self.assertEqual(only["agency_director"].mode, "only")
        self.assertEqual(only["agency_director"].role, "deep")
        kept = assignment_updates(MODEL, current, keep=True)
        self.assertEqual(kept["agency_director"].order, (MODEL, "x", "y"))
        self.assertEqual(kept["agency_director"].mode, "first")


class EverywhereApiTests(unittest.TestCase):
    def test_requires_admin_and_valid_model(self):
        from fastapi.testclient import TestClient

        import nuxiva_supervisor
        anonymous = TestClient(nuxiva_supervisor.admin)
        self.assertEqual(anonymous.post("/api/brains/everywhere", json={"model": MODEL}, headers=HEADERS).status_code, 401)
        client = TestClient(nuxiva_supervisor.admin)
        client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)
        self.assertEqual(client.post("/api/brains/everywhere", json={"model": "bad model"}, headers=HEADERS).status_code, 400)


if __name__ == "__main__":
    unittest.main()
