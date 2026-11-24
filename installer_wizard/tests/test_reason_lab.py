import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.authz import access_control
from agenti.reason_lab import api, lab, runner, store

SCENARIOS = [
    {"id": "weather", "category": "simple", "expected": {"intent": "weather_forecast", "effects": ["read"]},
     "texts": {"it": "che tempo fa a Roma", "en": "weather in Rome"}},
    {"id": "photo", "category": "composite", "expected": {"intent": "send_image", "effects": ["read", "send_external"]},
     "texts": {"it": "cerca un cane e inviamelo"}},
]


class FakeNative:
    def __init__(self, status=200):
        self.status = status
        self.calls = []
        self.keys = []

    def symbol(self, name):
        table = {
            "reason_lab_inspect": lambda raw: json.dumps({"scenarios": len(json.loads(raw)), "cases": 3, "by_language": {}, "by_category": {}}),
            "reason_lab_cases": lambda raw: json.dumps([
                {"id": f"{s['id']}.{lang}", "scenario": s["id"], "lang": lang, "category": s["category"], "text": text, "external_content": None}
                for s in json.loads(raw) for lang, text in s["texts"].items()]),
            "reason_lab_check_endpoint": lambda base: (_ for _ in ()).throw(ValueError("endpoint_forbidden")) if "169.254" in base else None,
            "reason_lab_run_case": self.run_case,
            "reason_lab_report": lambda scenarios, outcomes: json.dumps({"overall": {"cases": len(outcomes.strip().splitlines())}}),
            "reason_lab_rows": lambda scenarios, outcomes: json.dumps([
                {"case_id": json.loads(line)["case_id"], "lang": "it", "category": "simple", "expected_intent": "=cmd()", "intent": "x",
                 "intent_match": False, "success": False, "wrong_action": False, "completed": True, "tokens": 1, "latency_ms": 2}
                for line in outcomes.strip().splitlines()]),
        }
        return table.get(name)

    def run_case(self, backend, base, model, key, case_id, text, external, timeout):
        self.calls.append(case_id)
        self.keys.append(key)
        outcome = {"case_id": case_id, "intent": "x", "effects": ["read"], "completed": self.status == 200, "tokens": 5, "latency_ms": 7}
        return json.dumps({"status": self.status, "outcome": outcome})


class LabTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        patches = [mock.patch.object(store, "ROOT", Path(self.temp.name)), mock.patch.object(lab, "native_core", FakeNative())]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.runner = runner.Runner()
        self.app = FastAPI()
        self.app.include_router(api.admin_routes)
        self.app.dependency_overrides[require_admin] = lambda: "root"
        self.client = TestClient(self.app)
        accounts = {"root": {"role": "administrator", "nodes": ["*"]}}
        patch = mock.patch.object(access_control, "bindings", return_value=accounts)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch.object(api, "runner", self.runner)
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, name="main_set"):
        return self.client.put(f"/api/v5/reason-lab/datasets/{name}", json={"name": "Main", "scenarios": SCENARIOS})

    def test_requests_without_login_are_refused(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        self.assertEqual(TestClient(app).get("/api/v5/reason-lab/datasets").status_code, 401)

    def test_datasets_can_be_saved_listed_exported_and_deleted(self):
        self.assertEqual(self.save().status_code, 200)
        listing = self.client.get("/api/v5/reason-lab/datasets").json()["datasets"]
        self.assertEqual([d["id"] for d in listing], ["main_set"])
        exported = self.client.get("/api/v5/reason-lab/datasets/main_set/export")
        self.assertIn("attachment", exported.headers["content-disposition"])
        self.assertEqual(json.loads(exported.text)[0]["id"], "weather")
        self.assertEqual(self.client.delete("/api/v5/reason-lab/datasets/main_set").status_code, 200)
        self.assertEqual(self.client.get("/api/v5/reason-lab/datasets/main_set").status_code, 404)

    def test_identifiers_cannot_escape_the_storage_folder(self):
        for bad in ("..%2F..%2Fetc", "UPPER", "a", "x" * 60):
            self.assertIn(self.client.get(f"/api/v5/reason-lab/datasets/{bad}").status_code, (404, 422))
        self.assertEqual(self.client.get("/api/v5/reason-lab/runs/../../x").status_code, 404)
        self.assertEqual(self.client.get("/api/v5/reason-lab/runs/not-an-id").status_code, 422)

    def test_forbidden_endpoints_are_refused_for_profiles_and_runs(self):
        body = {"name": "Meta", "backend": "ollama", "base_url": "http://169.254.169.254", "model": "llama3"}
        self.assertEqual(self.client.put("/api/v5/reason-lab/profiles/meta", json=body).status_code, 422)
        self.save()
        run = {"dataset": "main_set", "backend": "ollama", "base_url": "http://169.254.169.254", "model": "llama3"}
        self.assertEqual(self.client.post("/api/v5/reason-lab/runs", json=run).status_code, 422)

    def test_profiles_never_store_keys(self):
        body = {"name": "Local", "backend": "ollama", "base_url": "http://127.0.0.1:11434", "model": "llama3:8b", "key": "secret-key"}
        self.assertEqual(self.client.put("/api/v5/reason-lab/profiles/local_one", json=body).status_code, 200)
        self.assertNotIn("secret-key", (Path(self.temp.name) / "profiles.json").read_text())
        self.assertEqual(self.client.get("/api/v5/reason-lab/profiles").json()["profiles"][0]["id"], "local_one")

    async def finished(self, run_id):
        await asyncio.wait_for(self.runner.tasks[run_id], 10)
        return store.load_run(run_id)

    async def test_a_run_completes_without_saving_the_key_and_writes_a_report(self):
        self.save()
        spec = {"dataset": "main_set", "backend": "openai", "base_url": "http://127.0.0.1:1234", "model": "m", "label": "t",
                "languages": [], "categories": [], "limit": 6000, "concurrency": 2, "timeout_seconds": 30}
        meta = await self.runner.start("root", spec, "top-secret")
        done = await self.finished(meta["id"])
        self.assertEqual((done["state"], done["done"], done["total"]), ("completed", 3, 3))
        self.assertTrue((store.run_dir(meta["id"]) / "report.json").exists())
        for path in Path(self.temp.name).rglob("*"):
            if path.is_file():
                self.assertNotIn("top-secret", path.read_text())
        self.assertEqual(set(lab.native_core.keys), {"top-secret"})

    async def test_filters_and_limits_choose_the_cases(self):
        self.save()
        spec = {"dataset": "main_set", "backend": "ollama", "base_url": "http://127.0.0.1:11434", "model": "m", "label": "",
                "languages": ["it"], "categories": ["composite"], "limit": 10, "concurrency": 1, "timeout_seconds": 30}
        meta = await self.runner.start("root", spec, None)
        self.assertEqual(meta["total"], 1)
        await self.finished(meta["id"])
        spec["categories"] = ["novel"]
        with self.assertRaises(Exception) as caught:
            await self.runner.start("root", spec, None)
        self.assertEqual(caught.exception.detail, "no_cases_selected")

    async def test_authentication_errors_stop_the_run_at_once(self):
        self.save()
        lab.native_core.status = 401
        spec = {"dataset": "main_set", "backend": "openai", "base_url": "http://127.0.0.1:1234", "model": "m", "label": "",
                "languages": [], "categories": [], "limit": 10, "concurrency": 1, "timeout_seconds": 30}
        meta = await self.runner.start("root", spec, "bad")
        done = await self.finished(meta["id"])
        self.assertEqual((done["state"], done["error"]), ("failed", "authentication_failed"))
        self.assertLess(len(lab.native_core.calls), 3)

    async def test_interrupted_runs_are_marked_after_a_restart(self):
        store.save_run({"id": "20260101000000-abcdef", "state": "running", "dataset": "x", "done": 1, "total": 2})
        self.runner.recover()
        self.assertEqual(store.load_run("20260101000000-abcdef")["state"], "interrupted")

    async def test_results_rows_and_downloads_neutralise_spreadsheet_formulas(self):
        self.save()
        spec = {"dataset": "main_set", "backend": "ollama", "base_url": "http://127.0.0.1:11434", "model": "m", "label": "",
                "languages": [], "categories": [], "limit": 10, "concurrency": 1, "timeout_seconds": 30}
        meta = await self.runner.start("root", spec, None)
        await self.finished(meta["id"])
        base = f"/api/v5/reason-lab/runs/{meta['id']}"
        self.assertEqual(self.client.get(base + "/rows?only=failed").json()["total"], 3)
        self.assertEqual(self.client.get(base + "/report").json()["report"]["overall"]["cases"], 3)
        csv = self.client.get(base + "/download?kind=csv")
        self.assertIn("'=cmd()", csv.text)
        self.assertIn("attachment", csv.headers["content-disposition"])
        self.assertEqual(self.client.get(base + "/download?kind=exe").status_code, 422)
        self.assertEqual(len(self.client.get(base + "/download?kind=outcomes").text.strip().splitlines()), 3)

    def test_without_the_native_module_the_lab_reports_it_clearly(self):
        with mock.patch.object(lab, "native_core", mock.Mock(symbol=lambda name: None)):
            self.assertFalse(self.client.get("/api/v5/reason-lab/status").json()["native"])
            response = self.client.post("/api/v5/reason-lab/datasets/inspect", json={"name": "x", "scenarios": SCENARIOS})
        self.assertEqual(response.status_code, 503)

    def test_a_viewer_cannot_run_or_edit(self):
        accounts = {"root": {"role": "viewer", "nodes": ["*"]}}
        with mock.patch.object(access_control, "bindings", return_value=accounts):
            self.assertEqual(self.client.get("/api/v5/reason-lab/datasets").status_code, 403)
            self.assertEqual(self.save().status_code, 403)
            self.assertEqual(self.client.post("/api/v5/reason-lab/runs", json={"dataset": "main_set", "backend": "ollama", "base_url": "http://127.0.0.1", "model": "m"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
