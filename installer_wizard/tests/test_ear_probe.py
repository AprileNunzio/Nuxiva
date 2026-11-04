import asyncio
import sys
import time
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import ear_probe


def fake_shell(show: str, journal: str = "", show_code: int = 0):
    calls: list[tuple[str, ...]] = []

    async def sh(*cmd: str, timeout: float = 0) -> tuple[int, str]:
        calls.append(cmd)
        if cmd[0] == "systemctl" and cmd[1] == "show":
            return show_code, show
        if cmd[0] == "journalctl":
            return 0, journal
        return 0, ""

    return sh, calls


def unit(active: str, sub: str, restarts: int, age_s: float | None) -> str:
    started = 0 if age_s is None else int((time.monotonic() - age_s) * 1_000_000)
    return (f"ActiveState={active}\nSubState={sub}\nNRestarts={restarts}\n"
            f"ExecMainStartTimestampMonotonic={started}\nResult=success")


class EarProbeTest(unittest.TestCase):

    def diagnose(self, show: str, journal: str = "", code: int = 0) -> dict:
        sh, _ = fake_shell(show, journal, code)
        return asyncio.run(ear_probe.diagnose(sh))

    def test_fresh_service_is_starting_not_down(self) -> None:
        result = self.diagnose(unit("active", "running", 0, 20))
        self.assertEqual(result["status"], "warn")
        self.assertTrue(result["starting"])

    def test_crash_loop_reports_last_error(self) -> None:
        journal = "avvio\nTraceback (most recent call last):\nModuleNotFoundError: No module named 'x'"
        result = self.diagnose(unit("activating", "auto-restart", 6, 1), journal)
        self.assertEqual(result["status"], "down")
        self.assertTrue(result["crashloop"])
        self.assertIn("No module named", result["detail"])
        self.assertNotIn("starting", result)

    def test_stopped_service(self) -> None:
        result = self.diagnose(unit("failed", "failed", 0, None))
        self.assertTrue(result["stopped"])
        self.assertEqual(result["status"], "down")

    def test_missing_unit(self) -> None:
        self.assertEqual(self.diagnose("", code=1)["status"], "down")

    def test_journal_text_is_sanitised(self) -> None:
        result = self.diagnose(unit("failed", "failed", 0, None), "RuntimeError: <script>\x1b[31m`rm`$x")
        self.assertNotIn("\x1b", result["detail"])
        self.assertNotIn("`", result["detail"])
        self.assertNotIn("$", result["detail"])
        self.assertNotIn("<", result["detail"])

    def test_recover_restarts_then_rebuilds(self) -> None:
        sh, calls = fake_shell("")
        rebuilt: list[bool] = []

        async def converge() -> None:
            rebuilt.append(True)

        asyncio.run(ear_probe.recover(sh, converge, {}, 1))
        self.assertIn(("systemctl", "restart", "nuxiva-ear"), calls)
        self.assertFalse(rebuilt)
        asyncio.run(ear_probe.recover(sh, converge, {"crashloop": True}, 1))
        self.assertEqual(rebuilt, [True])


if __name__ == "__main__":
    unittest.main()
