import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

DISPLAY = Path(__file__).resolve().parents[1] / "web" / "display"
LAB = DISPLAY / "agency" / "lab"
LANGS = ("it", "en", "fr", "es")
PROBE = """
const fs = require("fs");
const vm = require("vm");
const ctx = vm.createContext({ console });
ctx.window = ctx;
for (const name of ["layout", "behavior"]) vm.runInContext(fs.readFileSync(process.env.LAB_DIR + "/" + name + ".js", "utf8"), ctx);
const L = ctx.NuxivaLab;
const out = {};
const slot = L.layout.SLOTS[1];
const path = L.layout.pathBetween({ x: 0, z: 0, node: L.layout.nodeBeside(slot) }, { x: L.layout.REVIEW[0].x, z: L.layout.REVIEW[0].z });
out.pathStart = path[0];
out.pathEnd = path[path.length - 1];
out.slots = L.layout.SLOTS.length;
const agents = [
  { id: "a", status: "running", tasks: [{ id: "t1", status: "running", depends_on: [] }] },
  { id: "b", status: "pending", tasks: [{ id: "t2", status: "pending", depends_on: ["t1"] }] },
  { id: "c", status: "pending", tasks: [{ id: "t3", status: "pending", depends_on: [] }] },
  { id: "d", status: "failed", tasks: [] },
  { id: "e", status: "review", tasks: [] },
  { id: "f", status: "done", tasks: [] },
  { id: "g", status: "paused", tasks: [] },
  { id: "h", status: "weird", tasks: [] },
];
const plan = L.behavior.plan({ agents });
out.modes = Object.fromEntries([...plan.entries()].map(([k, v]) => [k, v.mode + (v.target ? ":" + v.target : "")]));
console.log(JSON.stringify(out));
"""


class AgencyLabTest(unittest.TestCase):
    def test_every_lab_file_stays_under_the_line_limit(self):
        for path in LAB.glob("*.js"):
            self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 500, path.name)

    def test_lab_code_has_no_comments(self):
        for path in LAB.glob("*.js"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                self.assertNotRegex(line.strip(), r"^(//|/\*)", f"{path.name}:{number}")

    def test_scripts_are_loaded_in_order(self):
        html = (DISPLAY / "display.html").read_text(encoding="utf-8")
        order = ["quality", "loader", "textures", "materials", "furniture", "layout", "room", "screen", "station",
                 "people", "behavior", "painters", "scene"]
        positions = []
        for name in order:
            self.assertTrue((LAB / f"{name}.js").is_file(), name)
            tag = f"/static/display/agency/lab/{name}.js"
            self.assertEqual(html.count(tag), 1, name)
            positions.append(html.index(tag))
        self.assertEqual(positions, sorted(positions))
        self.assertLess(positions[-1], html.index("/static/display/agency/office3d.js"))
        self.assertLess(html.index("/static/display/agency/office2d.js"), html.index("/static/display/agency/office3d.js"))

    def test_every_lab_text_key_exists_in_all_languages(self):
        used = set()
        for path in LAB.glob("*.js"):
            used.update(re.findall(r'"(lab_[a-z_]+)"', path.read_text(encoding="utf-8")))
        used.update(f"lab_state_{mode}" for mode in ("working", "waiting", "consulting", "review", "error", "done", "paused", "idle"))
        self.assertTrue(used)
        for lang in LANGS:
            dictionary = json.loads((DISPLAY / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            for key in used:
                self.assertIn(key, dictionary, f"{lang}:{key}")
                self.assertTrue(dictionary[key].strip(), f"{lang}:{key}")

    def test_characters_are_licensed_and_credited(self):
        loader = (LAB / "loader.js").read_text(encoding="utf-8")
        listed = set(re.findall(r'"(mini_[a-z]+_[a-f])"', loader))
        files = {p.stem for p in (LAB / "assets" / "characters").glob("*.glb")}
        self.assertEqual(listed, files)
        self.assertEqual(len(files), 12)
        credits = (LAB / "assets" / "CREDITS.md").read_text(encoding="utf-8")
        for token in ("CC0 1.0", "Kenney", "MIT", "meshoptimizer"):
            self.assertIn(token, credits)
        self.assertTrue((LAB / "assets" / "CC0-1.0.txt").is_file())
        self.assertTrue((LAB / "assets" / "vendor" / "MESHOPTIMIZER-LICENSE.md").is_file())
        notices = (DISPLAY.parents[2] / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("Mini Characters", notices)
        for path in (LAB / "assets" / "characters").glob("*.glb"):
            self.assertEqual(path.read_bytes()[:4], b"glTF")

    @unittest.skipUnless(shutil.which("node"), "node assente")
    def test_layout_routes_and_behavior_follow_real_states(self):
        done = subprocess.run(["node", "-e", PROBE], capture_output=True, text=True, timeout=30, env={**os.environ, "LAB_DIR": str(LAB)})
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)
        self.assertEqual(out["slots"], 8)
        self.assertEqual(out["pathEnd"], {"x": -2.0, "z": -3.1})
        self.assertEqual(out["modes"], {"a": "work", "b": "consult:a", "c": "wait", "d": "error", "e": "review",
                                         "f": "done", "g": "paused", "h": "idle"})


if __name__ == "__main__":
    unittest.main()
