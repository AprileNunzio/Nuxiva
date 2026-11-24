import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center.build_live import estimate, parse
from agenti.update_center.build_live.tracker import FORGET_AFTER, BuildLive

WEB = _ROOT / "installer_wizard" / "web"
LIB_BUILD = _ROOT / "scripts" / "os" / "lib_build.sh"


class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class ParseTests(unittest.TestCase):
    def test_reads_a_unit_event(self):
        self.assertEqual(parse.parse("unit nuxiva-native 6 366 tokio v1.41.0"),
                         {"event": "unit", "pkg": "nuxiva-native", "n": 6, "total": 366, "crate": "tokio v1.41.0"})

    def test_beat_without_crate(self):
        self.assertEqual(parse.parse("beat nuxiva-native 0 0")["crate"], None)

    def test_rejects_hostile_or_malformed_lines(self):
        for raw in ("", "unit", "boom nuxiva-native 1 2", "unit Nuxiva 1 2", "unit nuxiva-native -1 2",
                    "unit nuxiva-native 1 9999999", "unit nuxiva-native ١ 2", "unit nuxiva-native 1 2 " + "a" * 300,
                    "unit ../etc 1 2", None):
            self.assertIsNone(parse.parse(raw), raw)

    def test_drops_unsafe_crate_names(self):
        self.assertIsNone(parse.parse("unit nuxiva-native 1 2 <script> v1")["crate"])
        self.assertEqual(parse.parse("unit nuxiva-native 1 2 serde $(rm)")["crate"], "serde")


class EstimateTests(unittest.TestCase):
    def steady(self, done, total, step):
        return done, total, done * step, [i * step for i in range(1, done + 1)]

    def test_steady_pace(self):
        out = estimate.python_estimate(*self.steady(200, 300, 2.0))
        self.assertEqual(out["rate_per_min"], 30.0)
        self.assertEqual(out["remaining"], 100)
        self.assertAlmostEqual(out["eta"], 200.0, delta=1.0)
        self.assertEqual(out["confidence"], "high")
        self.assertLess(out["eta_low"], out["eta"])
        self.assertGreater(out["eta_high"], out["eta"])

    def test_early_estimate_is_uncertain(self):
        out = estimate.python_estimate(*self.steady(4, 366, 3.0))
        self.assertEqual(out["confidence"], "low")
        self.assertGreater(out["eta_high"], out["eta_low"] * 2)

    def test_no_eta_without_enough_data(self):
        self.assertIsNone(estimate.python_estimate(*self.steady(2, 366, 3.0))["eta"])
        self.assertIsNone(estimate.python_estimate(*self.steady(50, 0, 1.0))["eta"])
        self.assertIsNone(estimate.python_estimate(10, 20, float("nan"), [float("inf"), -1])["rate_per_min"])

    def test_finished_build_reports_zero(self):
        self.assertEqual(estimate.python_estimate(*self.steady(30, 30, 1.0))["eta"], 0.0)

    @unittest.skipUnless(estimate.RUST, "modulo nativo non disponibile")
    def test_rust_and_python_agree(self):
        for case in (self.steady(200, 300, 2.0), self.steady(4, 366, 3.0), self.steady(50, 0, 1.0),
                     (12, 40, 90.0, [1, 2, 5, 9, 14, 20, 30, 33, 41, 50, 60, 70])):
            self.assertEqual(estimate.estimate(*case), estimate.python_estimate(*case))


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.live = BuildLive(self.clock)

    def feed(self, raw, step="native"):
        return self.live.feed(step, raw)

    def test_idle_tracker_publishes_nothing(self):
        self.assertIsNone(self.live.public())

    def test_live_view_advances_with_units_and_beats(self):
        self.assertTrue(self.feed("start nuxiva-native 0 366"))
        for i in range(1, 7):
            self.clock.t += 2
            self.feed(f"unit nuxiva-native {i} 366 crate{i} v1.0.0")
        self.clock.t += 5
        self.feed("beat nuxiva-native 6 366 crate6 v1.0.0")
        view = self.live.public()
        cur = view["current"]
        self.assertEqual((cur["n"], cur["total"], cur["crate"]), (6, 366, "crate6 v1.0.0"))
        self.assertEqual(cur["last_beat"], self.clock.t)
        self.assertEqual(cur["last_unit"], self.clock.t - 5)
        self.assertEqual(view["now"], self.clock.t)
        self.assertIsNotNone(cur["estimate"]["eta"])
        self.assertEqual(cur["estimate"]["remaining"], 360)

    def test_done_closes_a_timed_segment(self):
        self.feed("start nuxiva-native 0 3")
        self.clock.t += 10
        self.feed("unit nuxiva-native 1 3 a")
        self.clock.t += 50
        self.feed("done nuxiva-native 0 3")
        view = self.live.public()
        self.assertIsNone(view["current"])
        self.assertEqual(view["segments"], [{"pkg": "nuxiva-native", "status": "done", "n": 1, "total": 3, "seconds": 60.0}])

    def test_a_new_package_closes_the_interrupted_one(self):
        self.feed("start nuxiva-native 0 3")
        self.clock.t += 5
        self.feed("start nuxiva-egress 0 9")
        view = self.live.public()
        self.assertEqual(view["segments"][0]["status"], "failed")
        self.assertEqual(view["current"]["pkg"], "nuxiva-egress")

    def test_rejects_bad_steps_and_lines(self):
        self.assertFalse(self.feed("start nuxiva-native 0 3", step="../x"))
        self.assertFalse(self.feed("garbage"))
        self.assertIsNone(self.live.public())

    def test_old_builds_are_forgotten(self):
        self.feed("start nuxiva-native 0 3")
        self.feed("done nuxiva-native 0 3")
        self.clock.t += FORGET_AFTER + 1
        self.assertIsNone(self.live.public())
        self.feed("start nuxiva-egress 0 3")
        self.assertEqual(self.live.public()["segments"], [])


@unittest.skipUnless(shutil.which("bash"), "bash non disponibile")
class ScriptTests(unittest.TestCase):
    def test_cargo_stream_emits_heartbeats_and_structured_events(self):
        script = f"""
progress() {{ echo "@@PROGRESS $1 ${{*:2}}"; }}
detail() {{ echo "@@DETAIL $*"; }}
info() {{ echo "[INFO] $*"; }}
warn() {{ echo "[WARN] $*"; }}
. "{LIB_BUILD}"
BUILD_HEARTBEAT=1
cargo_units() {{ echo 2; }}
fake() {{ echo "   Compiling a v1.0.0"; sleep 2.2; printf "   Comp"; sleep 1.2; echo "iling b v2.0.0"; }}
cargo_stream "Prova" 10 20 nuxiva-native fake
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.sh"
            path.write_text(script, encoding="utf-8")
            out = subprocess.run(["bash", str(path)], capture_output=True, text=True, timeout=30, check=True).stdout
        events = [line[8:] for line in out.splitlines() if line.startswith("@@BUILD ")]
        self.assertEqual(events[0], "start nuxiva-native 0 2")
        self.assertIn("unit nuxiva-native 1 2 a v1.0.0", events)
        self.assertIn("unit nuxiva-native 2 2 b v2.0.0", events)
        self.assertTrue(any(e.startswith("beat nuxiva-native 1 2") for e in events))
        self.assertEqual(events[-1], "done nuxiva-native 0 2")
        self.assertTrue(all(parse.parse(e) for e in events))
        ticks = [line for line in out.splitlines() if line.startswith("@@PROGRESS") and "1/2" in line]
        self.assertGreater(len({t.rsplit(" ", 1)[-1] for t in ticks}), 1)


class DisplayTests(unittest.TestCase):
    def test_every_live_key_is_translated(self):
        source = (WEB / "display" / "update_live.js").read_text(encoding="utf-8")
        keys = set(re.findall(r'"(upl_[a-z_]+)"', source))
        keys |= {f"upl_eta_range_{c}" for c in ("low", "medium", "high")}
        keys |= {"upl_pkg_" + p.replace("-", "_") for p in re.findall(r'"(nuxiva-[a-z]+)"', source)}
        self.assertGreater(len(keys), 20)
        for lang in ("it", "en", "fr", "es"):
            data = json.loads((WEB / "display" / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            self.assertFalse(keys - data.keys(), lang)

    def test_screen_loads_the_live_panel(self):
        html = (WEB / "display" / "display.html").read_text(encoding="utf-8")
        self.assertLess(html.index("update_live.js"), html.index("update_screen.js"))
        self.assertIn("update_live.css", html)

    @unittest.skipUnless(shutil.which("node"), "node non disponibile")
    def test_clock_format(self):
        runner = "globalThis.window = globalThis; require(process.argv[1]);" \
                 "process.stdout.write(JSON.stringify([5, 65, 3725, -3, NaN].map(window.NuxivaUpdateLive.clock)));"
        done = subprocess.run(["node", "-e", runner, str(WEB / "display" / "update_live.js")], capture_output=True,
                              text=True, timeout=30, check=True)
        self.assertEqual(json.loads(done.stdout), ["0:05", "1:05", "1:02:05", "0:00", "0:00"])

    @unittest.skipUnless(shutil.which("node"), "node non disponibile")
    def test_delta_reports_the_last_frame(self):
        runner = "require(process.argv[1]); process.stdout.write(String(globalThis.NuxivaDelta.lastFrameAt()));"
        done = subprocess.run(["node", "-e", runner, str(WEB / "shared" / "delta.js")], capture_output=True,
                              text=True, timeout=30, check=True)
        self.assertEqual(done.stdout, "0")


if __name__ == "__main__":
    unittest.main()
