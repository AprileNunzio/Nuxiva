import fcntl
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import termios
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIZ = ROOT / "installer_wizard"
LANG_DIR = WIZ / "bootstrap_language"
BOOTSTRAP = WIZ / "bootstrap.sh"
PICKER = WIZ / "lang_picker.sh"


def parse(path):
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        data[key] = value
    return data


def codes():
    return [p for p in sorted(LANG_DIR.glob("*.txt")) if p.name != "index.txt"]


def used_keys():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    return set(re.findall(r"T\[([a-z0-9_$]+)\]", text)) - {"s$CUR", "$key", "s$i", "_i"}


class LanguageFilesTest(unittest.TestCase):
    def test_every_language_has_the_same_keys(self):
        files = codes()
        reference = set(parse(LANG_DIR / "en.txt"))
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            self.assertEqual(set(parse(path)), reference, path.name)

    def test_every_key_used_by_bootstrap_is_translated(self):
        keys = set(parse(LANG_DIR / "en.txt"))
        missing = {k for k in used_keys() if not k.startswith("$")} - keys
        self.assertFalse(missing, missing)

    def test_format_placeholders_match_english(self):
        reference = parse(LANG_DIR / "en.txt")
        pattern = re.compile(r"%[sd]")
        for path in codes():
            for key, value in parse(path).items():
                self.assertEqual(pattern.findall(value), pattern.findall(reference[key]), f"{path.name}:{key}")

    def test_declared_languages_are_exactly_the_translated_ones(self):
        config = (WIZ / "backend" / "config.py").read_text(encoding="utf-8")
        block = re.search(r"UI_LANGUAGES = \{(.*?)\}", config, re.S).group(1)
        declared = set(re.findall(r'"([a-z]{2})":', block))
        picker = set(re.findall(r'"([a-z]{2})\|', PICKER.read_text(encoding="utf-8")))
        files = {p.stem for p in codes()}
        self.assertEqual(declared, picker)
        self.assertEqual(declared, files)
        for folder in (WIZ / "features" / "hardware" / "language", WIZ / "language"):
            self.assertTrue(all((folder / f"{c}.json").exists() for c in declared), folder)

    def test_no_control_characters(self):
        for path in codes():
            self.assertIsNone(re.search(r"[\x00-\x08\x0b-\x1f\x7f]", path.read_text(encoding="utf-8")), path.name)

    def test_bootstrap_has_no_hardcoded_italian_prompts(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("printf 'Premi", text)
        self.assertIn("choose_language", text)


@unittest.skipUnless(shutil.which("bash") and shutil.which("tput"), "bash required")
class PickerTest(unittest.TestCase):
    def drive(self, chunks):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        env = dict(os.environ, TERM="xterm", LANG="it_IT.UTF-8", LP_IDLE_LIMIT="30")
        script = f'source "{PICKER}"; lp_mouse_on() {{ :; }}; pick_language "$(lp_detect)"; echo "PICKED=$PICKED_LANG"'

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        proc = subprocess.Popen(["bash", "-c", script], stdin=slave, stdout=slave, stderr=slave,
                                env=env, close_fds=True, preexec_fn=attach_terminal)
        os.close(slave)
        out = b""

        def drain(seconds):
            nonlocal out
            end = time.time() + seconds
            while time.time() < end:
                ready, _, _ = select.select([master], [], [], 0.05)
                if ready:
                    try:
                        out += os.read(master, 65536)
                    except OSError:
                        return

        deadline = time.time() + 15
        while b"NUXIVA" not in out and time.time() < deadline:
            drain(0.2)
        drain(0.5)
        for chunk in chunks:
            os.write(master, chunk)
            drain(0.5)
        drain(1.0)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.fail(f"Picker did not exit. Terminal output: {out.decode(errors='replace')!r}")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)
        match = re.search(r"PICKED=(\w+)", out.decode(errors="replace"))
        return match.group(1) if match else None

    def test_enter_keeps_the_detected_language(self):
        self.assertEqual(self.drive([b"\n"]), "it")

    def test_arrow_keys_move_the_selection(self):
        self.assertEqual(self.drive([b"\x1b[B", b"\x1b[B", b"\n"]), "es")
        self.assertEqual(self.drive([b"\x1b[A", b"\n"]), "en")

    def test_mouse_click_selects_the_row(self):
        self.assertEqual(self.drive([b"\x1b[<0;10;7M"]), "fr")

    def test_mouse_wheel_scrolls(self):
        self.assertEqual(self.drive([b"\x1b[<65;1;1M", b"\n"]), "fr")


if __name__ == "__main__":
    unittest.main()
