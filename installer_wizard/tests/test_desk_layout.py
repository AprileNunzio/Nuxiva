import shutil
import subprocess
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parents[1] / "web" / "display" / "desk.js"
CSS = Path(__file__).resolve().parents[1] / "web" / "display" / "widgets_hud.css"


class LayoutSourceTest(unittest.TestCase):
    def test_widgets_are_borderless(self):
        rule = CSS.read_text().split("}")[0]
        for token in ("border: 0", "background: none", "backdrop-filter: none", "box-shadow: none"):
            self.assertIn(token, rule)

    def test_normal_widgets_stay_in_side_columns_and_sphere_is_kept_clear(self):
        source = DESK.read_text()
        self.assertIn("const sides = [{ x0: M, x1: M + colW }, { x0: W - M - colW, x1: W - M }]", source)
        self.assertIn("blocked.concat(keepOut, fixed)", source)
        self.assertNotIn("o.x - want.w - PIN_GAP", source.split("const sides")[1])

    @unittest.skipUnless(shutil.which("node"), "node assente")
    def test_syntax(self):
        done = subprocess.run(["node", "--check", str(DESK)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
