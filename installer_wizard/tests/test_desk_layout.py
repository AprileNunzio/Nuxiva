import shutil
import subprocess
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parents[1] / "web" / "display" / "desk.js"
GRID = Path(__file__).resolve().parents[1] / "web" / "display" / "desk_grid.js"
CSS = Path(__file__).resolve().parents[1] / "web" / "display" / "widgets_hud.css"


class LayoutSourceTest(unittest.TestCase):
    def test_widgets_are_borderless(self):
        rule = CSS.read_text().split("}")[0]
        for token in ("border: 0", "background: none", "backdrop-filter: none", "box-shadow: none"):
            self.assertIn(token, rule)

    def test_normal_widgets_distribute_across_columns_without_overlap(self):
        source = DESK.read_text()
        self.assertIn("colTops", source)
        self.assertIn("cols = Math.max(1", source)
        self.assertIn("colTops[chosen] = y + h + GAP", source)

    def test_lateral_first_and_center_keepout(self):
        source = DESK.read_text()
        self.assertIn("NuxivaDeskGrid.wings", source)
        self.assertIn("NuxivaDeskGrid.fit", source)
        self.assertIn("hooks.onStage(stage)", source)

    @unittest.skipUnless(shutil.which("node"), "node assente")
    def test_grid_never_overlaps_and_fills_outside_first(self):
        script = """
global.window = {};
require(process.argv[1]);
const G = window.NuxivaDeskGrid;
for (const W of [1024, 1920, 2560, 3840]) {
  const H = 1080, GAP = 14, TOP = 124, BOTTOM = H - 104, grid = G.wings(W, 26, GAP), tops = grid.xs.map(() => TOP);
  const pinned = [{ x: W - 320, y: 110, w: 300, h: 220 }], placed = [];
  const first = G.fit(grid, tops, 100, BOTTOM, pinned, GAP);
  if (![0, grid.xs.length - 1].includes(first.i)) throw new Error("not outer first " + W);
  for (let n = 0; n < 40; n++) {
    const h = 80 + (n * 53) % 220, spot = G.fit(grid, tops, h, BOTTOM, pinned.concat(placed), GAP);
    if (!spot) continue;
    const r = { x: grid.xs[spot.i], y: spot.y, w: grid.colW, h };
    for (const o of pinned.concat(placed)) if (r.x < o.x + o.w && o.x < r.x + r.w && r.y < o.y + o.h && o.y < r.y + r.h) throw new Error("overlap " + W);
    if (r.y + h > BOTTOM || r.x < 0 || r.x + r.w > W) throw new Error("outside " + W);
    placed.push(r); tops[spot.i] = r.y + h + GAP;
  }
  const leftEdge = Math.max(...grid.xs.filter((x) => x < W / 2).map((x) => x + grid.colW));
  const rightEdge = Math.min(...grid.xs.filter((x) => x > W / 2));
  if (rightEdge - leftEdge < 250) throw new Error("center too small " + W);
}
"""
        done = subprocess.run(["node", "-e", script, str(GRID)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    @unittest.skipUnless(shutil.which("node"), "node assente")
    def test_syntax(self):
        done = subprocess.run(["node", "--check", str(DESK)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
