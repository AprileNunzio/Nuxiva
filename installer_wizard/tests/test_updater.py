import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import updater


class UpdaterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bad_file = self.root / "bad_revs"
        self.pending_file = self.root / "update_pending.json"
        self.last_good = self.root / "last_good_rev"
        updater._ci.clear()
        updater._unreachable_since = 0.0

    def tearDown(self):
        self.tmp.cleanup()

    async def test_bad_revs_recording_and_clearing(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file):
            self.assertEqual(updater._bad_revs(), set())
            updater.mark_bad_rev("abc123456789")
            self.assertIn("abc123456789", updater._bad_revs())
            updater.clear_bad_rev("abc1234")
            self.assertEqual(updater._bad_revs(), set())

    async def test_bad_revs_cooldown_expiration(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file):
            self.bad_file.write_text(f"old1234 {time.time() - 3600}\n")
            self.assertEqual(updater._bad_revs(cooldown=1800), set())
            self.bad_file.write_text(f"recent1234 {time.time() - 60}\n")
            self.assertEqual(updater._bad_revs(cooldown=1800), {"recent1234"})

    async def test_ci_status_check_runs_success(self):
        payload = {
            "check_runs": [{"name": name, "status": "completed", "conclusion": "success"} for name in updater.GATED_JOBS]
        }
        res_mock = mock.MagicMock()
        res_mock.status_code = 200
        res_mock.json.return_value = payload
        res_mock.raise_for_status = mock.MagicMock()

        client_mock = mock.AsyncMock()
        client_mock.get.return_value = res_mock
        client_mock.__aenter__.return_value = client_mock

        with mock.patch("updater._slug", new_callable=mock.AsyncMock, return_value="AprileNunzio/Nuxiva"), \
                mock.patch("httpx.AsyncClient", return_value=client_mock):
            status = await updater.ci_status("111122223333")
            self.assertEqual(status, "success")

    async def test_ci_status_check_runs_failure(self):
        payload = {
            "check_runs": [
                {"name": "validate-python", "status": "completed", "conclusion": "failure"},
                {"name": "tests", "status": "completed", "conclusion": "success"},
            ]
        }
        res_mock = mock.MagicMock()
        res_mock.status_code = 200
        res_mock.json.return_value = payload
        res_mock.raise_for_status = mock.MagicMock()

        client_mock = mock.AsyncMock()
        client_mock.get.return_value = res_mock
        client_mock.__aenter__.return_value = client_mock

        with mock.patch("updater._slug", new_callable=mock.AsyncMock, return_value="AprileNunzio/Nuxiva"), \
                mock.patch("httpx.AsyncClient", return_value=client_mock):
            status = await updater.ci_status("444455556666")
            self.assertEqual(status, "failure")

    async def test_ci_workflow_success_does_not_replace_required_job_results(self):
        cr_mock = mock.MagicMock()
        cr_mock.status_code = 200
        cr_mock.json.return_value = {"check_runs": []}
        cr_mock.raise_for_status = mock.MagicMock()

        wf_mock = mock.MagicMock()
        wf_mock.status_code = 200
        wf_mock.json.return_value = {
            "workflow_runs": [
                {"name": "Nuxiva CI Pipeline", "status": "completed", "conclusion": "success"}
            ]
        }
        wf_mock.raise_for_status = mock.MagicMock()

        client_mock = mock.AsyncMock()
        client_mock.get.side_effect = [cr_mock, wf_mock]
        client_mock.__aenter__.return_value = client_mock

        with mock.patch("updater._slug", new_callable=mock.AsyncMock, return_value="AprileNunzio/Nuxiva"), \
                mock.patch("httpx.AsyncClient", return_value=client_mock):
            status = await updater.ci_status("777788889999")
            self.assertEqual(status, "pending")

    async def test_ci_requires_every_job_and_rejects_skipped_or_neutral_results(self):
        for missing in updater.GATED_JOBS:
            runs = [{"name": name, "status": "completed", "conclusion": "success"}
                    for name in updater.GATED_JOBS if name != missing]
            response = mock.Mock()
            client = mock.AsyncMock()
            client.__aenter__.return_value = client
            client.get.return_value = response
            with mock.patch("updater._slug", return_value="AprileNunzio/Nuxiva"), \
                    mock.patch("httpx.AsyncClient", return_value=client):
                for conclusion, expected in ((None, "pending"), ("skipped", "failure"), ("neutral", "failure")):
                    with self.subTest(missing=missing, conclusion=conclusion):
                        updater._ci.clear()
                        response.json.return_value = {"check_runs": runs + ([] if conclusion is None else
                            [{"name": missing, "status": "completed", "conclusion": conclusion}])}
                        self.assertEqual(await updater.ci_status("abc123"), expected)

    async def test_ci_uses_latest_result_for_each_exact_job_name(self):
        runs = [{"id": 2, "name": name, "status": "completed", "conclusion": "success"} for name in updater.GATED_JOBS]
        runs += [{"id": 1, "name": "tests", "status": "completed", "conclusion": "failure"},
                 {"id": 3, "name": "unrelated-tests", "status": "completed", "conclusion": "failure"}]
        response = mock.Mock()
        response.json.return_value = {"check_runs": runs}
        client = mock.AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = response
        with mock.patch("updater._slug", return_value="AprileNunzio/Nuxiva"), mock.patch("httpx.AsyncClient", return_value=client):
            self.assertEqual(await updater.ci_status("abc123"), "success")

    async def test_github_outage_never_bypasses_ci_after_an_hour(self):
        updater._unreachable_since = time.time() - 7200
        with mock.patch("updater.require_ci", return_value=True), \
                mock.patch("updater.git", return_value=(0, "abc123")), \
                mock.patch("updater.ci_status", return_value="unknown"):
            sha, note = await updater.pick_target("remote")
        self.assertEqual(sha, "")
        self.assertIn("attendo", note)

    async def test_ci_status_old_commit_with_no_runs_is_untested_not_pending(self):
        cr_mock = mock.MagicMock()
        cr_mock.status_code = 200
        cr_mock.json.return_value = {"check_runs": []}
        cr_mock.raise_for_status = mock.MagicMock()

        wf_mock = mock.MagicMock()
        wf_mock.status_code = 200
        wf_mock.json.return_value = {"workflow_runs": []}
        wf_mock.raise_for_status = mock.MagicMock()

        client_mock = mock.AsyncMock()
        client_mock.get.side_effect = [cr_mock, wf_mock]
        client_mock.__aenter__.return_value = client_mock

        old_time = str(int(time.time() - 7200))
        with mock.patch("updater._slug", new_callable=mock.AsyncMock, return_value="AprileNunzio/Nuxiva"), \
                mock.patch("httpx.AsyncClient", return_value=client_mock), \
                mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(0, old_time)):
            status = await updater.ci_status("aaaaabbbbb")
            self.assertEqual(status, "untested")

    async def test_pick_target_skips_bad_rev_in_auto_mode_and_reports_it(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file), \
                mock.patch("updater.require_ci", return_value=True), \
                mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(0, "bad1111\nold2222")), \
                mock.patch("updater.ci_status", new_callable=mock.AsyncMock) as ci_mock:
            updater.mark_bad_rev("bad1111")
            ci_mock.side_effect = lambda sha: "untested" if sha == "old2222" else "success"
            sha, note = await updater.pick_target("remote123", allow_bad=False)
            self.assertEqual(sha, "")
            self.assertIn("bad1111", note)

    async def test_pick_target_allows_bad_rev_when_allow_bad_true(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file), \
                mock.patch("updater.require_ci", return_value=True), \
                mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(0, "bad1111\nold2222")), \
                mock.patch("updater.ci_status", new_callable=mock.AsyncMock, return_value="success"):
            updater.mark_bad_rev("bad1111")
            sha, note = await updater.pick_target("remote123", allow_bad=True)
            self.assertEqual(sha, "bad1111")
            self.assertEqual(note, "")

    async def test_check_makes_available_even_if_target_was_previously_bad(self):
        info_dict = {}
        with mock.patch("updater.DEMO", False), \
                mock.patch("updater.store.update", info_dict), \
                mock.patch("updater.store.touch"), \
                mock.patch("updater.git", new_callable=mock.AsyncMock) as git_mock, \
                mock.patch("updater.pick_target", new_callable=mock.AsyncMock) as pick_mock:
            git_mock.side_effect = [
                (0, ""),
                (0, "local111"),
                (0, "remote999"),
                (0, "commit log"),
            ]
            pick_mock.side_effect = [("", "bad note"), ("target888", "")]
            res = await updater.check()
            self.assertTrue(res["available"])
            self.assertEqual(res["target_rev"], "target888")

    async def test_fetch_failure_invalidates_stale_update_target(self):
        info = {"available": True, "target_rev": "old-target", "remote_rev": "old-target", "last_result": "installed"}
        with mock.patch("updater.DEMO", False), mock.patch("updater.store.update", info), \
                mock.patch("updater.store.touch"), mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(1, "Could not resolve host: github.com")):
            result = await updater.check()
        self.assertFalse(result["available"])
        self.assertIsNone(result["target_rev"])
        self.assertIsNone(result["remote_rev"])
        self.assertIn("Could not resolve", result["check_error"])
        self.assertEqual(result["last_result"], "installed")

    async def test_successful_fetch_clears_transient_error(self):
        info = {"check_error": "dns failure", "last_result": "Fetch non riuscito: dns failure"}
        with mock.patch("updater.DEMO", False), mock.patch("updater.store.update", info), \
                mock.patch("updater.store.touch"), mock.patch("updater.git", new_callable=mock.AsyncMock) as git_mock:
            git_mock.side_effect = [(0, ""), (0, "same-rev"), (0, "same-rev"), (0, "")]
            result = await updater.check()
        self.assertIsNone(result["check_error"])
        self.assertIsNone(result["last_result"])

    async def test_forced_apply_never_uses_target_after_fetch_failure(self):
        with mock.patch("updater.check", new_callable=mock.AsyncMock, return_value={"check_error": "dns", "target_rev": "stale", "local_rev": "old"}), \
                mock.patch("updater.git", new_callable=mock.AsyncMock) as git_mock:
            self.assertFalse(await updater.apply(force=True))
            git_mock.assert_not_awaited()

    async def test_apply_force_clears_bad_rev_and_resets(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file), \
                mock.patch("updater.PENDING_FILE", self.pending_file), \
                mock.patch("updater.check", new_callable=mock.AsyncMock) as check_mock, \
                mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(0, "")), \
                mock.patch("updater.current_rev", new_callable=mock.AsyncMock, return_value="target999"), \
                mock.patch("updater.sh", new_callable=mock.AsyncMock, return_value=(0, "")), \
                mock.patch("updater.asyncio.sleep", new_callable=mock.AsyncMock):
            updater.mark_bad_rev("target999")
            check_mock.return_value = {
                "available": True,
                "target_rev": "target999",
                "local_rev": "local111",
                "remote_rev": "target999",
            }
            applied = await updater.apply("manuale", force=True)
            self.assertTrue(applied)
            self.assertNotIn("target999", updater._bad_revs())
            self.assertTrue(self.pending_file.exists())
            pending_data = json.loads(self.pending_file.read_text())
            self.assertEqual(pending_data["to"], "target999")

    async def test_finish_pending_cleans_bad_rev_on_success(self):
        with mock.patch("updater.BAD_REVS_FILE", self.bad_file), \
                mock.patch("updater.PENDING_FILE", self.pending_file), \
                mock.patch("updater.current_rev", new_callable=mock.AsyncMock, return_value="good999"), \
                mock.patch("updater.mark_good", new_callable=mock.AsyncMock):
            updater.mark_bad_rev("good999")
            self.pending_file.write_text(json.dumps({"from": "old", "to": "good999", "at": time.time()}))
            rollback = await updater.finish_pending(True)
            self.assertFalse(rollback)
            self.assertNotIn("good999", updater._bad_revs())
            self.assertFalse(self.pending_file.exists())

    async def test_apply_refuses_when_revision_does_not_change(self):
        with mock.patch("updater.PENDING_FILE", self.pending_file), \
                mock.patch("updater.check", new_callable=mock.AsyncMock) as check_mock, \
                mock.patch("updater.git", new_callable=mock.AsyncMock, return_value=(0, "")), \
                mock.patch("updater.current_rev", new_callable=mock.AsyncMock, return_value="local111"), \
                mock.patch("updater.sh", new_callable=mock.AsyncMock) as sh_mock:
            check_mock.return_value = {"available": True, "target_rev": "target999", "local_rev": "local111",
                                       "remote_rev": "target999"}
            applied = await updater.apply("manuale")
            self.assertFalse(applied)
            self.assertFalse(self.pending_file.exists())
            self.assertIn("non applicato", check_mock.return_value["last_result"])
            sh_mock.assert_not_called()

    async def test_finish_pending_does_not_claim_success_on_wrong_revision(self):
        with mock.patch("updater.PENDING_FILE", self.pending_file), \
                mock.patch("updater.current_rev", new_callable=mock.AsyncMock, return_value="old0000"), \
                mock.patch("updater.mark_good", new_callable=mock.AsyncMock) as good_mock:
            self.pending_file.write_text(json.dumps({"from": "old0000", "to": "new9999", "at": time.time()}))
            await updater.finish_pending(True)
            good_mock.assert_not_called()
            self.assertIn("non attivo", updater.store.update["last_result"])


if __name__ == "__main__":
    unittest.main()
