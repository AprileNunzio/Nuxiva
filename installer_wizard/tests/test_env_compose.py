import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from env_format import format_line


@unittest.skipUnless(shutil.which("docker"), "Docker CLI unavailable")
class ComposeEnvironmentTest(unittest.TestCase):
    def test_configuration_values_are_literal_in_docker_compose(self):
        version = subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=15)
        if version.returncode:
            self.skipTest("Docker Compose unavailable")
        values = {"LITERAL": "$HOME ${NUXIVA_TEST_MISSING} `printf UNEXPECTED`", "APOSTROPHE": "it's $HOME",
                  "PATH_VALUE": r"C:\models\new", "BACKSLASH": r"literal\$HOME", "DOUBLE_DOLLAR": "a$$b"}
        with tempfile.TemporaryDirectory(prefix="nuxiva-env-compose-") as directory:
            path = Path(directory)
            environment = path / "test.env"
            compose = path / "compose.yml"
            environment.write_text("\n".join(format_line(k, v) for k, v in values.items()) + "\n", encoding="utf-8")
            compose.write_text("services:\n  check:\n    image: alpine:3.20\n    environment:\n      LITERAL: ${LITERAL}\n", encoding="utf-8")
            result = subprocess.run(["docker", "compose", "--env-file", str(environment), "-f", str(compose),
                                     "config", "--environment"], capture_output=True, text=True, timeout=30, check=True)
        actual = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        for key, value in values.items():
            self.assertEqual(actual[key], value, key)
