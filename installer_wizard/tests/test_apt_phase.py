import asyncio
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import updater
from agenti.update_center.apt_phase import parse, runner, stream
from agenti.update_center.apt_phase.state import AptPhase

SAMPLES = [
    "0% [Working]\r\x1b[33mGet:1 http://deb.debian.org/debian bookworm InRelease\x1b[0m\x07",
    "Get:2 https://user:secret@repo.example.com/apt?token=abc stable InRelease",
    "Hit:3 http://security.debian.org bookworm-security InRelease",
    "Err:4 http://x.org stable Release",
    "Reading package lists...",
    "3 upgraded, 1 newly installed, 2 to remove and 4 not upgraded.",
    "Unpacking libc6:amd64 (2.36-9+deb12u7) over (2.36-9+deb12u4) ...",
    "Setting up openssl (3.0.15-1~deb12u1) ...",
    "Processing triggers for man-db (2.11.2-2) ...",
    "Unpacking $(rm) (1) ...",
    "E: Could not get lock /var/lib/dpkg/lock-frontend",
    "W: Some index files failed to download",
    "a b\tc   d",
    "é" * 400,
    "",
]


class ParseTests(unittest.TestCase):
    def test_sanitizes_escapes_and_credentials(self):
        first = parse._py_classify(SAMPLES[0])
        self.assertEqual(first["text"], "Get:1 http://deb.debian.org/debian bookworm InRelease")
        self.assertEqual(first["kind"], "fetch")
        second = parse._py_classify(SAMPLES[1])["text"]
        self.assertEqual(second, "Get:2 https://***@repo.example.com/apt stable InRelease")
        self.assertNotIn("secret", second)
        self.assertNotIn("token", second)

    def test_classifies_dpkg_lines_and_rejects_hostile_packages(self):
        self.assertEqual(parse._py_classify(SAMPLES[6])["package"], "libc6")
        self.assertEqual(parse._py_classify(SAMPLES[7])["kind"], "setup")
        self.assertEqual(parse._py_classify(SAMPLES[8])["kind"], "trigger")
        self.assertIsNone(parse._py_classify(SAMPLES[9])["package"])
        self.assertEqual(parse._py_classify(SAMPLES[10])["kind"], "error")
        self.assertEqual(parse._py_classify(SAMPLES[3])["kind"], "warn")

    def test_summary_and_percent(self):
        line = parse._py_classify(SAMPLES[5])
        self.assertEqual(line["summary"], {"upgraded": 3, "installed": 1, "removed": 2, "held": 4})
        self.assertEqual(parse._py_percent(line["summary"], 4, 2), 75)
        self.assertEqual(parse._py_percent(line["summary"], 40, 40), 100)
        self.assertEqual(parse._py_percent(None, 4, 2), 0)
        self.assertEqual(parse._py_percent({"upgraded": 0, "installed": 0}, 0, 0), 100)

    def test_truncates_long_lines(self):
        text = parse._py_classify(SAMPLES[13])["text"]
        self.assertTrue(text.endswith("…"))
        self.assertLessEqual(len(text.encode("utf-8")), parse.MAX_LINE + 3)

    @unittest.skipUnless(parse.RUST, "nuxiva_native non installato")
    def test_rust_and_python_agree(self):
        for raw in SAMPLES:
            self.assertEqual(parse.classify(raw), parse._py_classify(raw), raw)
        summary = {"upgraded": 3, "installed": 1, "removed": 0, "held": 0}
        self.assertEqual(parse.percent(summary, 4, 2), parse._py_percent(summary, 4, 2))


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.phase = AptPhase(Path(self.tmp.name) / "logs")

    def tearDown(self):
        self.phase.close()
        self.tmp.cleanup()

    def test_run_progress_public_view_and_private_log(self):
        self.phase.begin()
        self.phase.step("update", "running")
        self.phase.feed(SAMPLES[1])
        self.phase.feed(SAMPLES[2])
        self.phase.step("update", "done")
        self.assertEqual(self.phase.data["percent"], 30)
        self.phase.step("upgrade", "running")
        self.phase.feed(SAMPLES[5])
        self.phase.feed(SAMPLES[6])
        self.phase.feed(SAMPLES[7])
        self.assertEqual(self.phase.data["percent"], 30 + 70 * 25 // 100)
        self.phase.step("upgrade", "done")
        self.phase.finish("done")
        view = self.phase.public()
        self.assertEqual((view["status"], view["percent"], view["fetched"]), ("done", 100, 2))
        self.assertTrue(all(set(line) == {"k", "t"} for line in view["lines"]))
        self.assertFalse(any("secret" in line["t"] for line in view["lines"]))
        logs = list((Path(self.tmp.name) / "logs").glob("*.log"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(stat.S_IMODE(logs[0].stat().st_mode), 0o600)
        content = logs[0].read_text()
        self.assertIn("### finish done", content)
        self.assertNotIn("secret", content)

    def test_public_lines_are_bounded_and_logs_pruned(self):
        for _ in range(13):
            self.phase.begin()
            for i in range(40):
                self.phase.feed(f"Get:{i} http://deb.debian.org/debian bookworm InRelease")
            self.phase.finish("done")
        self.assertLessEqual(len(self.phase.public()["lines"]), 14)
        self.assertLessEqual(len(list((Path(self.tmp.name) / "logs").glob("*.log"))), 10)

    def test_rejects_unknown_steps_and_statuses(self):
        self.phase.begin()
        with self.assertRaises(ValueError):
            self.phase.step("rm", "running")
        with self.assertRaises(ValueError):
            self.phase.finish("hacked")

    def test_idle_is_hidden_and_skip_is_reported(self):
        self.assertIsNone(self.phase.public())
        self.phase.skip("not_root")
        self.assertEqual((self.phase.public()["status"], self.phase.public()["error"]), ("skipped", "not_root"))


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_lines_and_exit_code(self):
        seen = []
        script = "import sys; sys.stdout.write('uno\\r\\ndue\\ntre'); sys.stdout.flush(); sys.exit(3)"
        code = await stream.run([sys.executable, "-c", script], seen.append, 20)
        self.assertEqual((code, seen), (3, ["uno", "due", "tre"]))

    async def test_timeout_kills_the_process(self):
        with self.assertRaises(stream.StreamTimeout):
            await stream.run([sys.executable, "-c", "import time; time.sleep(30)"], lambda _: None, 0.5)

    async def test_environment_is_minimal(self):
        seen = []
        with mock.patch.dict("os.environ", {"NUXIVA_SECRET_X": "leak"}):
            await stream.run([sys.executable, "-c", "import os; print(os.environ.get('NUXIVA_SECRET_X', 'none'))"],
                             seen.append, 20)
        self.assertEqual(seen, ["none"])


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.phase = AptPhase(Path(self.tmp.name) / "logs")
        self.events = []
        self.touches = []

    def tearDown(self):
        self.phase.close()
        self.tmp.cleanup()

    def _patches(self, codes):
        calls = []

        async def fake_run(cmd, on_line, timeout):
            calls.append(cmd)
            on_line("Get:1 http://deb.debian.org/debian bookworm InRelease")
            return codes[len(calls) - 1]

        return calls, [
            mock.patch.object(runner, "skip_reason", return_value=None),
            mock.patch.object(runner, "LOCK_FILE", Path(self.tmp.name) / "apt.lock"),
            mock.patch.object(runner.stream, "run", side_effect=fake_run),
        ]

    async def _run(self, codes):
        calls, patches = self._patches(codes)
        for p in patches:
            p.start()
        try:
            result = await runner.run(lambda level, msg: self.events.append(level), lambda: self.touches.append(1),
                                      self.phase)
        finally:
            for p in patches:
                p.stop()
        return result, calls

    async def test_runs_update_then_upgrade_with_fixed_commands(self):
        result, calls = await self._run([0, 0])
        self.assertEqual(result, "done")
        self.assertEqual([c[-1] for c in calls], ["update", "upgrade"])
        self.assertTrue(all("apt-get" in c and "DEBIAN_FRONTEND=noninteractive" in c for c in calls))
        self.assertIn("--with-new-pkgs", calls[1])
        self.assertEqual(self.phase.data["steps"], {"update": "done", "upgrade": "done"})
        self.assertTrue(self.touches)

    async def test_failure_is_reported_and_upgrade_still_attempted(self):
        result, calls = await self._run([100, 0])
        self.assertEqual(result, "failed")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.phase.data["error"], "apt_update")
        self.assertIn("ERROR", self.events)

    async def test_skips_without_root_or_apt(self):
        with mock.patch.object(runner, "skip_reason", return_value="not_root"):
            result = await runner.run(lambda *a: None, lambda: None, self.phase)
        self.assertEqual((result, self.phase.data["status"]), ("skipped", "skipped"))

    async def test_lock_prevents_parallel_runs(self):
        lock = Path(self.tmp.name) / "apt.lock"
        held = runner._acquire(lock)
        self.assertIsNotNone(held)
        try:
            self.assertIsNone(runner._acquire(lock))
            with mock.patch.object(runner, "skip_reason", return_value=None), \
                    mock.patch.object(runner, "LOCK_FILE", lock):
                self.assertEqual(await runner.run(lambda *a: None, lambda: None, self.phase), "busy")
        finally:
            runner._release(held)

    def test_disabled_by_env(self):
        with mock.patch.object(runner, "env_get", return_value="0"):
            self.assertEqual(runner.skip_reason(), "disabled")


class UpdaterIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_system_packages_run_before_nuxiva_pipeline(self):
        order = []
        info = {"available": True, "target_rev": "t" * 40, "local_rev": "l" * 40, "remote_rev": "t" * 40}
        tracker = mock.Mock()
        tracker.begin.side_effect = lambda *a: order.append("nuxiva")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("updater.PENDING_FILE", Path(tmp) / "pending.json"), \
                mock.patch("updater.check", new_callable=mock.AsyncMock, return_value=info), \
                mock.patch("updater._system_packages", new_callable=mock.AsyncMock,
                           side_effect=lambda: order.append("apt")), \
                mock.patch("updater._tracker", return_value=tracker), \
                mock.patch("agenti.update_center.guard.preflight", new_callable=mock.AsyncMock, return_value=False), \
                mock.patch("updater._record", new_callable=mock.AsyncMock), \
                mock.patch("updater.mark_bad_rev"):
            self.assertFalse(await updater.apply("manuale"))
        self.assertEqual(order, ["apt", "nuxiva"])

    async def test_setup_flow_can_skip_system_packages(self):
        info = {"available": True, "target_rev": "t" * 40, "local_rev": "l" * 40, "remote_rev": "t" * 40}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("updater.PENDING_FILE", Path(tmp) / "pending.json"), \
                mock.patch("updater.check", new_callable=mock.AsyncMock, return_value=info), \
                mock.patch("updater._system_packages", new_callable=mock.AsyncMock) as system, \
                mock.patch("updater._tracker", return_value=mock.Mock()), \
                mock.patch("agenti.update_center.guard.preflight", new_callable=mock.AsyncMock, return_value=False), \
                mock.patch("updater._record", new_callable=mock.AsyncMock), \
                mock.patch("updater.mark_bad_rev"):
            await updater.apply("setup_initial", system_first=False)
        system.assert_not_awaited()

    async def test_concurrent_apply_is_refused(self):
        gate = asyncio.Event()

        async def slow(*args, **kwargs):
            await gate.wait()
            return {"check_error": "x"}

        with mock.patch("updater.check", side_effect=slow):
            first = asyncio.create_task(updater.apply("automatico"))
            await asyncio.sleep(0)
            self.assertFalse(await updater.apply("manuale"))
            gate.set()
            self.assertFalse(await first)


if __name__ == "__main__":
    unittest.main()
