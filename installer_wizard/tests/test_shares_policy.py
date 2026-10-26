import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.shares import policy, status

STEP = Path(__file__).resolve().parents[2] / "scripts" / "os" / "steps" / "63-shares.sh"


def render(env: dict) -> str:
    script = re.search(r"python3 - \"\$CONF\".*?<<'PY'\n(.*?)\nPY\n", STEP.read_text(encoding="utf-8"), re.S).group(1)
    with tempfile.TemporaryDirectory() as tmp:
        conf = Path(tmp) / "smb.conf"
        conf.write_text("[global]\n   workgroup = WORKGROUP\n", encoding="utf-8")
        clean = {k: v for k, v in os.environ.items() if not k.startswith("NUXIVA_SHARES")}
        subprocess.run([sys.executable, "-", str(conf), "nuxiva-share", "/srv/nuxiva/condivisa", "/srv/nuxiva/condivisioni"],
                       input=script, text=True, env={**clean, **env}, check=True)
        return conf.read_text(encoding="utf-8")


class PolicyTest(unittest.TestCase):
    def test_networks_are_validated_and_fall_back_to_home_ranges(self):
        self.assertEqual(policy.networks(""), policy.DEFAULT_NETWORKS)
        self.assertEqual(policy.networks("192.168.1.0/24, 10.1.2.3 ; 192.168."), ("192.168.1.0/24", "10.1.2.3", "192.168."))
        for bad in ("0.0.0.0/0x", "evil.example.com", "300.1.1.1", "192.168.1.0/24 rm -rf"):
            self.assertEqual(policy.networks(bad), policy.DEFAULT_NETWORKS, bad)

    def test_read_clamps_every_value(self):
        env = {"NUXIVA_SHARES_PROTOCOL": "SMB1", "NUXIVA_SHARES_ENCRYPT": "x", "NUXIVA_SHARES_UPLOAD_MB": "999999",
               "NUXIVA_SHARES_READONLY": "1", "NUXIVA_SHARES_RECYCLE": "1", "NUXIVA_SHARES_DISCOVERY": "0"}
        with mock.patch.object(policy, "env_get", side_effect=lambda k, d="": env.get(k, d)):
            result = policy.read()
        self.assertEqual((result["protocol"], result["encrypt"], result["upload_mb"]), ("SMB2_10", "default", 1000))
        self.assertTrue(result["readonly"] and result["recycle"])
        self.assertFalse(result["discovery"])


class SessionsTest(unittest.TestCase):
    def test_smbstatus_output_is_parsed_and_noise_ignored(self):
        output = ("\nSamba version 4.19\nPID     Username     Group        Machine                                   Protocol Version  Encryption           Signing\n"
                  "----------------------------------------------------------------------------------------------------------------------------------------\n"
                  "1234    nuxiva-share nuxiva-share pc-casa (ipv4:192.168.1.20:5555)     SMB3_11           -                    partial(AES-128-CMAC)\n")
        rows = status.parse(output)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["user"], rows[0]["protocol"]), ("nuxiva-share", "SMB3_11"))


class StepConfigTest(unittest.TestCase):
    def test_defaults_keep_the_previous_behaviour(self):
        conf = render({})
        self.assertIn("server min protocol = SMB2_10", conf)
        self.assertIn("read only = no", conf)
        self.assertIn("hosts allow = 127. 10. 172.16.0.0/12 192.168.", conf)
        self.assertNotIn("vfs objects", conf)
        self.assertNotIn("smb encrypt", conf)

    def test_hardened_options_are_written(self):
        conf = render({"NUXIVA_SHARES_READONLY": "1", "NUXIVA_SHARES_RECYCLE": "1", "NUXIVA_SHARES_PROTOCOL": "SMB3_11",
                       "NUXIVA_SHARES_ENCRYPT": "required", "NUXIVA_SHARES_NETWORKS": "192.168.1.0/24"})
        for line in ("read only = yes", "vfs objects = recycle", "server min protocol = SMB3_11", "server smb encrypt = required",
                     "server signing = mandatory", "hosts allow = 192.168.1.0/24"):
            self.assertIn(line, conf)

    def test_hostile_values_never_reach_the_configuration(self):
        conf = render({"NUXIVA_SHARES_NETWORKS": "10.0.0.0/8\n[evil]\n   path = /", "NUXIVA_SHARES_PROTOCOL": "SMB1\n[x]"})
        self.assertNotIn("[evil]", conf)
        self.assertNotIn("[x]", conf)
        self.assertIn("server min protocol = SMB2_10", conf)
        self.assertIn("hosts allow = 127. 10. 172.16.0.0/12 192.168.", conf)


if __name__ == "__main__":
    unittest.main()
