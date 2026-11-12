import asyncio
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center import telemetry


class FakeShell:

    def __init__(self, inspect: tuple[int, str]) -> None:
        self.inspect = inspect
        self.calls: list[tuple[str, ...]] = []

    async def __call__(self, *cmd, timeout: float = 0) -> tuple[int, str]:
        self.calls.append(cmd)
        if cmd[0] == "systemctl":
            return 3, "\n".join("active" if unit != "nuxiva-core" else "inactive" for unit in telemetry.UNITS)
        return self.inspect


def run(sh: FakeShell, runtime: str) -> dict:
    telemetry._services.update(at=0.0, runtime=None, items=[])
    return {item["unit"]: item["state"] for item in asyncio.run(telemetry.services(sh, runtime))}


class ContainerStateTests(unittest.TestCase):

    def test_health_wins_over_running(self):
        self.assertEqual(telemetry.container_state(0, "running healthy\n"), "active")
        self.assertEqual(telemetry.container_state(0, "running starting"), "activating")
        self.assertEqual(telemetry.container_state(0, "running unhealthy"), "failed")

    def test_plain_states_without_healthcheck(self):
        self.assertEqual(telemetry.container_state(0, "running "), "active")
        self.assertEqual(telemetry.container_state(0, "exited"), "inactive")
        self.assertEqual(telemetry.container_state(0, "restarting"), "activating")
        self.assertEqual(telemetry.container_state(0, "dead"), "failed")

    def test_missing_container_or_unexpected_output(self):
        self.assertEqual(telemetry.container_state(1, "Error: No such object: nuxiva-core"), "inactive")
        self.assertEqual(telemetry.container_state(0, ""), "unknown")
        self.assertEqual(telemetry.container_state(0, "<script>"), "unknown")


class ServicesTests(unittest.TestCase):

    def test_docker_core_reports_container_health(self):
        sh = FakeShell((0, "running healthy"))
        states = run(sh, "docker")
        self.assertEqual(states["nuxiva-core"], "active")
        self.assertEqual(states["nuxiva-display"], "active")
        self.assertIn(("docker", "inspect", "--format", telemetry.INSPECT_FORMAT, "nuxiva-core"), sh.calls)

    def test_docker_core_unhealthy_is_failed(self):
        self.assertEqual(run(FakeShell((0, "running unhealthy")), "docker")["nuxiva-core"], "failed")

    def test_native_core_uses_systemd_only(self):
        sh = FakeShell((0, "running healthy"))
        self.assertEqual(run(sh, "native")["nuxiva-core"], "inactive")
        self.assertFalse(any(call[0] == "docker" for call in sh.calls))

    def test_cache_is_scoped_to_runtime(self):
        sh = FakeShell((0, "running healthy"))
        telemetry._services.update(at=0.0, runtime=None, items=[])
        asyncio.run(telemetry.services(sh, "native"))
        states = {i["unit"]: i["state"] for i in asyncio.run(telemetry.services(sh, "docker"))}
        self.assertEqual(states["nuxiva-core"], "active")


class PrivacyVeilTests(unittest.TestCase):

    def test_veil_is_translated_and_wired(self):
        import json
        web = _ROOT / "installer_wizard" / "web" / "display"
        for lang in ("it", "en", "fr", "es"):
            text = json.loads((web / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]["privacy_veil"]
            self.assertTrue(text.strip())
        self.assertIn('data-i18n="privacy_veil"', (web / "display.html").read_text(encoding="utf-8"))
        self.assertIn("audience.gate === true", (web / "presence" / "shutter.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
