import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from features.update_center import history


class UpdateHistoryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.history_file = self.root / "update_history.json"
        self.state_dir = self.root / "var/lib/nuxiva"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.patcher1 = mock.patch("features.update_center.history.UPDATE_HISTORY_FILE", self.history_file)
        self.patcher2 = mock.patch("features.update_center.history.STATE_DIR", self.state_dir)
        self.patcher1.start()
        self.patcher2.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.tmp.cleanup()

    def test_parse_commit_records_multiline_it_en(self):
        body_sample = (
            "Titolo del commit / Commit subject\n\n"
            "Descrizione dettagliata delle novità in italiano.\n"
            "- Aggiunta funzionalità X\n"
            "- Verifiche eseguite\n\n"
            "Detailed description in English.\n"
            "- Added feature X\n"
            "- Verified tests\n"
        )
        raw = (
            f"1111222233334444555566667777888899990000{history.GIT_FIELD_SEP}"
            f"Nunzio Aprile{history.GIT_FIELD_SEP}"
            f"1792400000{history.GIT_FIELD_SEP}"
            f"Titolo del commit / Commit subject{history.GIT_FIELD_SEP}"
            f"{body_sample}{history.GIT_RECORD_SEP}"
        )
        records = history.parse_commit_records(raw)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["sha"], "1111222233334444555566667777888899990000")
        self.assertEqual(r["short_sha"], "1111222")
        self.assertEqual(r["author"], "Nunzio Aprile")
        self.assertEqual(r["timestamp"], 1792400000.0)
        self.assertEqual(r["title"], "Titolo del commit / Commit subject")
        self.assertEqual(r["body"], body_sample.strip())

    async def test_extract_commits_with_range_and_fallback(self):
        async def fake_git(*args, **kwargs):
            cmd = args[0]
            if cmd == "log":
                target = args[-1]
                if ".." in target:
                    # Multi-commit range
                    c1 = (
                        f"aaaabbbbcccc1111222233334444555566667777{history.GIT_FIELD_SEP}"
                        f"Dev{history.GIT_FIELD_SEP}1792401000{history.GIT_FIELD_SEP}"
                        f"Commit 2 / Second commit{history.GIT_FIELD_SEP}Body 2{history.GIT_RECORD_SEP}"
                    )
                    c2 = (
                        f"ddddffff00001111222233334444555566667777{history.GIT_FIELD_SEP}"
                        f"Dev{history.GIT_FIELD_SEP}1792400500{history.GIT_FIELD_SEP}"
                        f"Commit 1 / First commit{history.GIT_FIELD_SEP}Body 1{history.GIT_RECORD_SEP}"
                    )
                    return (0, c1 + c2)
                else:
                    return (0, (
                        f"single111122223333444455556666777788889999{history.GIT_FIELD_SEP}"
                        f"Dev{history.GIT_FIELD_SEP}1792401000{history.GIT_FIELD_SEP}"
                        f"Single commit{history.GIT_FIELD_SEP}Single body{history.GIT_RECORD_SEP}"
                    ))
            return (1, "error")

        # Range test
        commits = await history.extract_commits(fake_git, from_rev="rev_start", to_rev="rev_end")
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]["title"], "Commit 2 / Second commit")
        self.assertEqual(commits[1]["title"], "Commit 1 / First commit")

        # Fallback single test
        single = await history.extract_commits(fake_git, from_rev=None, to_rev="single1111222")
        self.assertEqual(len(single), 1)
        self.assertEqual(single[0]["title"], "Single commit")

    async def test_extract_commits_when_git_fails_returns_empty(self):
        async def failing_git(*args, **kwargs):
            return (128, "fatal: bad object")

        commits = await history.extract_commits(failing_git, from_rev="bad_rev1", to_rev="bad_rev2")
        self.assertEqual(commits, [])

    async def test_record_update_and_deduplication(self):
        async def fake_git(*args, **kwargs):
            return (0, (
                f"235785ce6be3309b182e7027232f04ed14bd0b30{history.GIT_FIELD_SEP}"
                f"Nunzio Aprile{history.GIT_FIELD_SEP}1792402000{history.GIT_FIELD_SEP}"
                f"Pannello di controllo / Control Panel{history.GIT_FIELD_SEP}Note complete{history.GIT_RECORD_SEP}"
            ))

        ts = time.time()
        record = await history.record_update(
            fake_git,
            to_rev="235785ce6be3309b182e7027232f04ed14bd0b30",
            from_rev="023c7bc20397d534d63ba82c679936ab46dd9499",
            status="installed",
            reason="automatico",
            installed_at=ts,
        )
        self.assertEqual(record["status"], "installed")
        self.assertEqual(record["to_short"], "235785c")
        self.assertEqual(record["from_short"], "023c7bc")
        self.assertEqual(record["commit_count"], 1)
        self.assertEqual(record["commits"][0]["title"], "Pannello di controllo / Control Panel")

        # Confirm that file was persisted
        loaded = history.load_history()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["to_rev"], "235785ce6be3309b182e7027232f04ed14bd0b30")

        # Deduplication: running record_update again with same parameters within 24h does NOT add a duplicate
        dup = await history.record_update(
            fake_git,
            to_rev="235785ce6be3309b182e7027232f04ed14bd0b30",
            from_rev="023c7bc20397d534d63ba82c679936ab46dd9499",
            status="installed",
            reason="automatico",
            installed_at=ts + 10,
        )
        self.assertEqual(dup["id"], record["id"])
        loaded_again = history.load_history()
        self.assertEqual(len(loaded_again), 1, "Duplicate record must not be created")

    async def test_record_rollback_and_failure(self):
        async def fake_git(*args, **kwargs):
            return (0, "")

        record_failed = await history.record_update(
            fake_git,
            to_rev="target_fail",
            from_rev="start_rev",
            status="failed",
            reason="manuale",
            error="Aggiornamento non applicato: git reset error",
        )
        self.assertEqual(record_failed["status"], "failed")
        self.assertEqual(record_failed["error"], "Aggiornamento non applicato: git reset error")

        record_rollback = await history.record_update(
            fake_git,
            to_rev="target_bad",
            from_rev="good_rev",
            status="rollback",
            reason="automatico",
            error="Rollback a good_rev",
        )
        self.assertEqual(record_rollback["status"], "rollback")
        self.assertEqual(record_rollback["error"], "Rollback a good_rev")

        loaded = history.load_history()
        self.assertEqual(len(loaded), 2)
        # Newest record is first
        self.assertEqual(loaded[0]["status"], "rollback")
        self.assertEqual(loaded[1]["status"], "failed")

    def test_pagination_and_limits(self):
        records = [
            {
                "id": f"rec_{i}",
                "status": "installed",
                "to_rev": f"sha_{i:04d}",
                "to_short": f"{i:04d}",
                "from_rev": None,
                "from_short": None,
                "installed_at": float(1792400000 + i),
                "installed_at_iso": "2026-10-19T00:00:00Z",
                "reason": "automatico",
                "commits": [],
                "commit_count": 0,
            }
            for i in range(25)
        ]
        history.save_history(records)

        # Page 1: limit 10, offset 0
        p1 = history.get_history_page(offset=0, limit=10)
        self.assertEqual(p1["total"], 25)
        self.assertEqual(len(p1["records"]), 10)
        self.assertEqual(p1["records"][0]["id"], "rec_0")
        self.assertEqual(p1["records"][9]["id"], "rec_9")

        # Page 2: limit 10, offset 10
        p2 = history.get_history_page(offset=10, limit=10)
        self.assertEqual(len(p2["records"]), 10)
        self.assertEqual(p2["records"][0]["id"], "rec_10")

        # Page 3: limit 10, offset 20
        p3 = history.get_history_page(offset=20, limit=10)
        self.assertEqual(len(p3["records"]), 5)
        self.assertEqual(p3["records"][0]["id"], "rec_20")

    def test_empty_or_corrupt_history_file(self):
        self.history_file.write_text("corrupted json content")
        with self.assertLogs(history.log, level="WARNING"):
            loaded = history.load_history()
        self.assertEqual(loaded, [])

    def test_api_history_route(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import auth
        from features.update_center import api as upd_api

        app = FastAPI()
        app.include_router(upd_api.admin_routes)

        anon = TestClient(app)
        admin = TestClient(app)
        admin.cookies.set(auth.SESSION_COOKIE, auth.issue("root"))

        # Anonymous must be 401
        self.assertEqual(anon.get("/api/v5/updater/history").status_code, 401)

        # Admin without history records
        res = admin.get("/api/v5/updater/history?limit=5&offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("records", data)
        self.assertIn("total", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
        self.assertIn("events", data)
        self.assertEqual(data["records"], [])
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["offset"], 0)


if __name__ == "__main__":
    unittest.main()
