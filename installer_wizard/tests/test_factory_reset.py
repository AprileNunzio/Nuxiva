import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.factory_reset import api, catalog, challenge, engine, service


def populate(root: Path) -> None:
    (root / "state/people/anna").mkdir(parents=True)
    (root / "state/people/anna/face.npy").write_bytes(b"x" * 4096)
    (root / "state/voiceprints").mkdir()
    (root / "state/voiceprints/anna.json").write_text("{}")
    (root / "state/ear_review/journal").mkdir(parents=True)
    (root / "state/ear_review/journal/journal.key").write_bytes(b"k" * 44)
    (root / "state/ear_review/journal/journal.db").write_bytes(b"d" * 9000)
    (root / "state/backups").mkdir()
    (root / "state/backups/nuxiva-aaaaaaaaaaaa.tar.gz").write_bytes(b"b" * 100)
    (root / "state/vault.json").write_text("{}")
    (root / "state/setup.json").write_text('{"done": true}')
    (root / "etc").mkdir()
    (root / "etc/session.key").write_bytes(b"s" * 32)
    (root / "etc/core-native.env").write_text("A=1\n")
    (root / "etc/nuxiva.env").write_text(
        "NUXIVA_MACHINE=pc\nNUXIVA_ASSISTANT_NAME=Jarvis\nNUXIVA_SECRET_KEY=old\nNUXIVA_TELEGRAM_TOKEN=abc\n# nota\nNUXIVA_LLM_MODEL=qwen\n")
    (root / "log").mkdir()
    (root / "log/events.log").write_text("hello")


def plan_for(root: Path, **extra) -> dict:
    return {"id": "t1", "by": "admin", "state": str(root / "state"), "etc": str(root / "etc"), "log": str(root / "log"),
            "keep_state": [], "keep_etc": sorted(catalog.KEEP_ETC), "keep_env": sorted(catalog.KEEP_ENV),
            "rotate_env": sorted(catalog.ROTATE_ENV), "services": [], **extra}


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "a" / "b"
        self.root.mkdir(parents=True)
        populate(self.root)

    def test_everything_is_erased_and_verified(self):
        report = engine.execute(plan_for(self.root))
        self.assertEqual(report["status"], "verified")
        self.assertEqual(sorted(p.name for p in (self.root / "state").iterdir()), ["factory_reset.json", "setup.json"])
        self.assertEqual(json.loads((self.root / "state/setup.json").read_text())["done"], False)
        self.assertEqual(list((self.root / "log").iterdir()), [])
        self.assertFalse((self.root / "etc/session.key").exists())
        self.assertGreaterEqual(report["canaries"]["checked"], 3)
        self.assertEqual(report["canaries"]["survivors"], 0)
        self.assertEqual(report["leftovers"], {})

    def test_report_is_private_and_lists_no_personal_names(self):
        engine.execute(plan_for(self.root))
        path = self.root / "state/factory_reset.json"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("anna", path.read_text())

    def test_env_keeps_hardware_keys_rotates_secrets_drops_the_rest(self):
        report = engine.execute(plan_for(self.root))
        rows = dict(engine.parse_env((self.root / "etc/nuxiva.env").read_text()))
        self.assertEqual(rows["NUXIVA_MACHINE"], "pc")
        self.assertEqual(rows["NUXIVA_LLM_MODEL"], "qwen")
        self.assertNotEqual(rows["NUXIVA_SECRET_KEY"], "old")
        self.assertEqual(len(rows["NUXIVA_SECRET_KEY"]), 64)
        self.assertIn("NUXIVA_VOICESTUDIO_KEY", rows)
        self.assertNotIn("NUXIVA_TELEGRAM_TOKEN", rows)
        self.assertNotIn("NUXIVA_ASSISTANT_NAME", rows)
        self.assertEqual(report["env"]["removed"], 2)
        self.assertEqual((self.root / "etc/nuxiva.env").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / "etc/core-native.env").read_text(), "A=1\n")

    def test_kept_backups_survive_and_are_reported(self):
        report = engine.execute(plan_for(self.root, keep_state=["backups"]))
        self.assertEqual(report["status"], "verified")
        self.assertTrue((self.root / "state/backups/nuxiva-aaaaaaaaaaaa.tar.gz").exists())
        self.assertEqual(report["kept"], ["backups"])

    def test_without_keeping_backups_they_are_deleted(self):
        engine.execute(plan_for(self.root))
        self.assertFalse((self.root / "state/backups").exists())

    def test_symlinks_are_removed_but_never_followed(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "precious.txt").write_text("keep me")
        (self.root / "state/link").symlink_to(outside)
        engine.execute(plan_for(self.root))
        self.assertEqual((outside / "precious.txt").read_text(), "keep me")
        self.assertFalse(os.path.lexists(self.root / "state/link"))

    def test_small_files_are_overwritten_before_unlink(self):
        target = self.root / "state/vault.json"
        target.write_text("secret-material")
        seen = []
        real = engine.shred

        def spy(path, info):
            real(path, info)
            if path == target:
                seen.append(path.read_bytes())

        with mock.patch.object(engine, "shred", spy):
            engine.execute(plan_for(self.root))
        self.assertEqual(seen, [bytes(len("secret-material"))])

    def test_unsafe_roots_and_untrusted_plans_are_refused(self):
        for bad in ("/", "/var", "relative/path", "/var/lib/../etc/x"):
            with self.assertRaises(engine.PlanError):
                engine.check_root(bad)
        link = Path(self.tmp.name) / "l1" / "l2"
        link.parent.mkdir()
        link.symlink_to(self.root)
        with self.assertRaises(engine.PlanError):
            engine.check_root(str(link))
        plan_file = self.root / "plan.json"
        plan_file.write_text("{}")
        os.chmod(plan_file, 0o644)
        with self.assertRaises(engine.PlanError):
            engine.load_plan(plan_file)
        os.chmod(plan_file, 0o600)
        self.assertEqual(engine.load_plan(plan_file), {})

    def test_incomplete_when_something_cannot_be_removed(self):
        real = engine.erase

        def failing(path, device, counters):
            if path.name == "vault.json":
                counters["failed"] += 1
                return
            real(path, device, counters)

        with mock.patch.object(engine, "erase", failing):
            report = engine.execute(plan_for(self.root))
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("vault.json", report["leftovers"]["state"])

    def test_scan_counts_files_and_bytes(self):
        rows = {row["name"]: row for row in engine.scan(self.root / "state")}
        self.assertEqual(rows["people"]["files"], 1)
        self.assertEqual(rows["people"]["bytes"], 4096)
        self.assertNotIn("backups", {row["name"] for row in engine.scan(self.root / "state", frozenset({"backups"}))})

    def test_plan_file_is_destroyed_by_main(self):
        plan_file = Path(self.tmp.name) / "plan.json"
        plan_file.write_text(json.dumps(plan_for(self.root)))
        os.chmod(plan_file, 0o600)
        self.assertEqual(engine.main(["engine", str(plan_file)]), 0)
        self.assertFalse(plan_file.exists())
        self.assertEqual(engine.main(["engine"]), 2)


class ChallengeTest(unittest.TestCase):
    def setUp(self):
        self.book = challenge.Challenges()
        self.options = {"keep_backups": False, "include_shares": False}

    def issue(self, user="admin", now=1000.0):
        return self.book.issue(user, self.options, now)

    def test_phrase_shape_and_token_are_random(self):
        first, second = self.issue(), self.issue("other")
        self.assertRegex(first["phrase"], r"^RESET-[A-Z2-9]{6}$")
        self.assertNotEqual(first["token"], second["token"])

    def test_too_early_then_valid_once(self):
        item = self.issue()
        with self.assertRaises(challenge.ChallengeError) as early:
            self.book.redeem(item["token"], "admin", item["phrase"], self.options, 1002.0)
        self.assertEqual(early.exception.status, 425)
        self.book.redeem(item["token"], "admin", item["phrase"], self.options, 1010.0)
        with self.assertRaises(challenge.ChallengeError) as again:
            self.book.redeem(item["token"], "admin", item["phrase"], self.options, 1011.0)
        self.assertEqual(again.exception.code, "challenge_invalid")

    def test_expiry_wrong_user_and_changed_options(self):
        item = self.issue()
        with self.assertRaises(challenge.ChallengeError):
            self.book.redeem(item["token"], "admin", item["phrase"], self.options, 1000 + challenge.TTL + 1)
        item = self.issue()
        with self.assertRaises(challenge.ChallengeError):
            self.book.redeem(item["token"], "mallory", item["phrase"], self.options, 1020.0)
        item = self.issue()
        with self.assertRaises(challenge.ChallengeError) as changed:
            self.book.redeem(item["token"], "admin", item["phrase"], {"keep_backups": True, "include_shares": False}, 1020.0)
        self.assertEqual(changed.exception.code, "challenge_options_changed")

    def test_three_wrong_phrases_burn_the_challenge(self):
        item = self.issue()
        for _ in range(challenge.MAX_ATTEMPTS):
            with self.assertRaises(challenge.ChallengeError) as wrong:
                self.book.redeem(item["token"], "admin", "RESET-AAAAAA", self.options, 1020.0)
            self.assertEqual(wrong.exception.code, "phrase_mismatch")
        with self.assertRaises(challenge.ChallengeError) as burned:
            self.book.redeem(item["token"], "admin", item["phrase"], self.options, 1020.0)
        self.assertEqual(burned.exception.code, "challenge_invalid")

    def test_new_challenge_replaces_the_old_one_for_the_same_user(self):
        old = self.issue()
        new = self.issue()
        with self.assertRaises(challenge.ChallengeError):
            self.book.redeem(old["token"], "admin", old["phrase"], self.options, 1020.0)
        self.book.redeem(new["token"], "admin", new["phrase"], self.options, 1020.0)

    def test_active_challenges_are_capped(self):
        for index in range(challenge.MAX_ACTIVE + 3):
            self.book.issue(f"user{index}", self.options, 1000.0 + index)
        self.assertEqual(len(self.book.rows), challenge.MAX_ACTIVE)


class CatalogTest(unittest.TestCase):
    def test_known_and_unknown_names(self):
        self.assertEqual(catalog.domain_of("voiceprints"), "people")
        self.assertEqual(catalog.domain_of("vault.json"), "accounts")
        self.assertEqual(catalog.domain_of("backups"), "backups")
        self.assertEqual(catalog.domain_of("mystery"), catalog.OTHER)

    def test_group_sums_and_sorts_by_size(self):
        rows = [{"name": "people", "files": 2, "bytes": 10}, {"name": "faces", "files": 1, "bytes": 5},
                {"name": "vault.json", "files": 1, "bytes": 100}]
        out = catalog.group(rows, [{"name": "a.log", "files": 3, "bytes": 7}], [{"name": "session.key", "files": 1, "bytes": 32}])
        self.assertEqual(out[0]["id"], "accounts")
        by = {row["id"]: row for row in out}
        self.assertEqual(by["people"]["files"], 3)
        self.assertEqual(by["logs"]["bytes"], 7)
        self.assertEqual(by["configuration"]["items"], 1)

    def test_services_are_stopped_supervisor_first(self):
        self.assertEqual(catalog.SERVICES[0], "nuxiva-supervisor")


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "a" / "b"
        self.root.mkdir(parents=True)
        populate(self.root)
        patches = (mock.patch.object(service, "STATE_DIR", self.root / "state"), mock.patch.object(service, "ETC_DIR", self.root / "etc"),
                   mock.patch.object(service, "LOG_DIR", self.root / "log"), mock.patch.object(service, "REPORT", self.root / "state/factory_reset.json"),
                   mock.patch.object(service, "DEMO", True), mock.patch.object(service.store, "event"),
                   mock.patch.object(api.auth, "authenticate", side_effect=lambda user, password, ip: password == "good"),
                   mock.patch.object(api.auth, "rate_limited", return_value=False),
                   mock.patch.object(challenge, "MIN_WAIT", 0.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        challenge.challenges.rows.clear()
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def test_inventory_lists_domains_and_totals(self):
        body = self.client.get("/api/factory-reset/inventory").json()
        ids = {row["id"] for row in body["domains"]}
        self.assertTrue({"people", "accounts", "logs", "backups", "configuration"} <= ids)
        self.assertGreater(body["files"], 5)
        self.assertEqual(body["blockers"], [])
        self.assertIsNone(body["last"])
        kept = self.client.get("/api/factory-reset/inventory?keep_backups=true").json()
        self.assertNotIn("backups", {row["id"] for row in kept["domains"]})
        self.assertEqual(kept["kept"], ["backups"])

    def test_wrong_password_is_refused(self):
        self.assertEqual(self.client.post("/api/factory-reset/challenge", json={"password": "bad"}).status_code, 403)

    def test_unknown_fields_are_rejected(self):
        self.assertEqual(self.client.post("/api/factory-reset/challenge", json={"password": "good", "x": 1}).status_code, 422)

    def test_rate_limited_clients_are_stopped_before_checking_the_password(self):
        with mock.patch.object(api.auth, "rate_limited", return_value=True):
            self.assertEqual(self.client.post("/api/factory-reset/challenge", json={"password": "good"}).status_code, 429)

    def test_busy_system_blocks_the_challenge(self):
        with mock.patch.object(service, "blockers", return_value=["system_busy"]):
            self.assertEqual(self.client.post("/api/factory-reset/challenge", json={"password": "good"}).status_code, 409)

    def test_full_flow_wipes_and_reports(self):
        issued = self.client.post("/api/factory-reset/challenge", json={"password": "good"}).json()
        wrong = self.client.post("/api/factory-reset/execute", json={"token": issued["token"], "phrase": "RESET-AAAAAA"})
        self.assertEqual(wrong.status_code, 403)
        self.assertTrue((self.root / "state/vault.json").exists())
        with mock.patch.object(service.threading, "Thread") as thread:
            thread.side_effect = lambda target, args, **_: mock.Mock(start=lambda: target(*args))
            done = self.client.post("/api/factory-reset/execute", json={"token": issued["token"], "phrase": issued["phrase"]})
        self.assertEqual(done.status_code, 202)
        self.assertFalse((self.root / "state/vault.json").exists())
        report = self.client.get("/api/factory-reset/report").json()
        self.assertEqual(report["status"], "verified")
        again = self.client.post("/api/factory-reset/execute", json={"token": issued["token"], "phrase": issued["phrase"]})
        self.assertEqual(again.status_code, 403)

    def test_changed_options_invalidate_the_token(self):
        issued = self.client.post("/api/factory-reset/challenge", json={"password": "good"}).json()
        response = self.client.post("/api/factory-reset/execute",
                                    json={"token": issued["token"], "phrase": issued["phrase"], "include_shares": True})
        self.assertEqual(response.status_code, 409)
        self.assertTrue((self.root / "state/vault.json").exists())

    def test_missing_report_is_404(self):
        self.assertEqual(self.client.get("/api/factory-reset/report").status_code, 404)

    def test_plan_never_leaks_into_the_wipe_set(self):
        plan = service.build_plan("admin", False, False)
        self.assertEqual(plan["services"], [])
        self.assertNotIn("password", json.dumps(plan))
        path = service.write_plan(plan)
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
