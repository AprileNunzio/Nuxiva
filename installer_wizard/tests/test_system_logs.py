import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.system_logs import api, service
from features.authz import access_control


class SystemLogsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        service._catalog_cache.clear()

    def tearDown(self):
        self.temp.cleanup()

    def test_secrets_and_csv_formulas_are_not_exported_as_executable_cells(self):
        text = service.redact('NUXIVA_SECRET_KEY=real-secret password="my-password" Authorization: Bearer abc123 https://user:secret@example.test/a')
        for value in ("real-secret", "my-password", "abc123", "user:secret"):
            self.assertNotIn(value, text)
        self.assertIn("REDACTED", text)
        for header in ('Authorization: Basic dXNlcjpwYXNz', 'Cookie: session=first-value; csrf=second-value'):
            redacted = service.redact(header)
            for secret in ('dXNlcjpwYXNz', 'first-value', 'second-value'):
                self.assertNotIn(secret, redacted)
        for secret in ['"password": "two secret words"', "password='two secret words'", 'api-key="escaped \\" secret"']:
            self.assertNotIn("secret", service.redact(secret).split("[REDACTED]")[-1])
            self.assertNotIn("two", service.redact(secret))
        payload = {"entries": [service.normalize('=HYPERLINK("https://example.test")', "source")]}
        csv, media = service.export(payload, "csv")
        self.assertIn("text/csv", media)
        self.assertIn("'=HYPERLINK", csv)

    def test_journal_priority_wins_and_exceptions_are_detected(self):
        self.assertEqual(service.normalize("ERROR was handled", "journal", priority="6")["severity"], "info")
        row = service.normalize("ModuleNotFoundError: No module named 'cryptography'", "core")
        self.assertEqual(row["severity"], "error")
        self.assertEqual(row["severity_source"], "inferred")
        self.assertIsNone(service.timestamp("not-a-date"))

    def test_file_tail_is_bounded(self):
        file = self.root / "service.log"
        file.write_text("old\n" * 1000 + "last-one\nlast-two\n", encoding="utf-8")
        self.assertEqual(service.tail_file(file, 2, max_bytes=100), ["last-one", "last-two"])

    async def test_sources_are_discovered_and_private_paths_are_not_exposed(self):
        (self.root / "new-service.log").write_text("actual log", encoding="utf-8")
        with mock.patch.object(service, "LOG_DIR", self.root), mock.patch.object(service, "local_node_id", return_value="host"), mock.patch.object(service.shutil, "which", return_value=None):
            catalog = await service.discover("local")
        self.assertTrue(any(item["name"] == "new-service.log" for item in catalog["sources"]))
        self.assertNotIn("_path", json.dumps(api.public_catalog(catalog)))
        self.assertEqual(catalog["scope"], "local")

    async def test_remote_device_never_receives_host_logs(self):
        audit = self.root / "audit.jsonl"
        now = datetime.now(timezone.utc).isoformat()
        audit.write_text("\n".join(json.dumps(row) for row in [
            {"ts": now, "msg": "host event mentioning remote", "level": "ERROR"},
            {"ts": now, "msg": "selected device event", "level": "INFO", "node_id": "remote"},
            {"ts": now, "msg": "other device event", "level": "ERROR", "node_id": "other"},
        ]), encoding="utf-8")
        with mock.patch.object(service, "local_node_id", return_value="host"), mock.patch.object(service, "AUDIT_FILE", audit), mock.patch.object(service, "sh", new_callable=mock.AsyncMock) as command:
            data = await service.entries("events", "remote", 60, 100, "all", "")
            self.assertEqual([row["message"] for row in data["entries"]], ["selected device event"])
            self.assertEqual(data["scope"], "server_events_only")
            with self.assertRaises(KeyError):
                await service.entries("journal", "remote", 60, 100, "all", "")
            command.assert_not_awaited()

    async def test_structured_journal_filters_and_analysis_use_actual_records(self):
        now = time.time()
        events = [json.dumps({"MESSAGE": "ModuleNotFoundError: missing dependency", "PRIORITY": "3", "__REALTIME_TIMESTAMP": str(int(now * 1_000_000)), "_SYSTEMD_UNIT": "nuxiva-core.service"}), json.dumps({"MESSAGE": "ready", "PRIORITY": "6", "__REALTIME_TIMESTAMP": str(int(now * 1_000_000))})]
        catalog = {"sources": [{"id": "journal", "kind": "journal"}], "scope": "local", "warnings": []}
        with mock.patch.object(service, "discover", new_callable=mock.AsyncMock, return_value=catalog), mock.patch.object(service, "sh", new_callable=mock.AsyncMock, return_value=(0, "\n".join(events))):
            data = await service.entries("journal", "local", 60, 100, "error", "dependency")
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(data["counts"]["error"], 1)
        self.assertEqual(data["analysis"], [{"code": "python_dependency_missing", "occurrences": 1}])
        self.assertTrue(data["redacted"])

    def test_api_requires_login_and_rejects_unbounded_requests(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        client = TestClient(app)
        self.assertEqual(client.get("/api/v5/logs/sources").status_code, 401)
        app.dependency_overrides[require_admin] = lambda: "user"
        self.assertEqual(client.get("/api/v5/logs/entries?limit=999999").status_code, 422)
        self.assertEqual(client.get("/api/v5/logs/entries?node_id=../../etc").status_code, 422)
        self.assertEqual(client.get("/api/v5/logs/export?format=html").status_code, 422)

    def test_download_preserves_scope_and_redacted_content(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "user"
        payload = {"entries": [service.normalize("password=private-value", "node")], "node_id": "remote", "scope": "server_events_only"}
        with mock.patch.object(service, "entries", new_callable=mock.AsyncMock, return_value=payload):
            response = TestClient(app).get("/api/v5/logs/export?node_id=remote&format=json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertEqual(response.json()["node_id"], "remote")
        self.assertNotIn("private-value", response.text)

    def test_exports_and_other_devices_are_denied_without_explicit_permission(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "auditor"
        client = TestClient(app)
        accounts = {"auditor": {"role": "auditor", "nodes": ["node-a"]}}
        grants = {**access_control.ROLE_GRANTS, "auditor": {"logs.read"}}
        with mock.patch.object(access_control, "bindings", return_value=accounts), mock.patch.object(access_control, "ROLE_GRANTS", grants), mock.patch.object(service, "entries", new_callable=mock.AsyncMock) as read:
            for url in ("/export?node_id=node-a&format=csv", "/entries?node_id=node-a&format=json", "/entries?node_id=node-b"):
                self.assertEqual(client.get("/api/v5/logs" + url).status_code, 403)
            read.assert_not_awaited()

    async def test_a_full_scan_is_marked_even_when_no_remote_events_match(self):
        audit = self.root / "audit.jsonl"
        audit.write_text('\n'.join(json.dumps({"msg": "host only", "node_id": "other"}) for _ in range(2)), encoding="utf-8")
        with mock.patch.object(service, "local_node_id", return_value="host"), mock.patch.object(service, "AUDIT_FILE", audit):
            result = await service.entries("events", "remote", 60, 2, "all", "")
        self.assertEqual(result["entries"], [])
        self.assertTrue(result["limit_reached"])

    async def test_diagnostic_report_does_not_attach_host_hardware_to_remote_device(self):
        payload = {"node_id": "remote", "warnings": [], "entries": []}
        catalog = {"scope": "server_events_only", "sources": [{"id": "events", "name": "Nuxiva", "_path": "/private"}]}
        with mock.patch.object(service, "discover", new_callable=mock.AsyncMock, return_value=catalog), mock.patch.object(service.psutil, "virtual_memory") as memory:
            report = await service.diagnostics(payload)
        memory.assert_not_called()
        self.assertIsNone(report["machine"])
        self.assertIn("remote_logs_not_exposed", report["limitations"])
        self.assertNotIn("_path", report["sources"][0])
