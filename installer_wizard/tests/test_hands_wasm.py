import asyncio
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from agenti.hands import display_api

ROOT = Path(__file__).resolve().parents[1]
WASM_DIR = ROOT / "web" / "display" / "hands" / "wasm"
RUNNER = """
const fs = require("fs"), vm = require("vm");
const dir = process.argv[1];
const sandbox = { console, URL, TextEncoder, TextDecoder, WebAssembly, FinalizationRegistry };
vm.createContext(sandbox);
sandbox.bytes = fs.readFileSync(dir + "/hands_core_bg.wasm");
vm.runInContext(fs.readFileSync(dir + "/hands_core.js", "utf8") + ";wasm_bindgen.initSync({ module: bytes });globalThis.wb = wasm_bindgen;", sandbox);
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const hand = (x, y) => ({ handedness: "right", score: 0.9, points: Array.from({ length: 21 }, (_, i) => [x + i * 0.004, y - i * 0.004, 0]) });
const out = cases.map(({ faces, audience, trust }) => {
  const engine = new sandbox.wb.WasmHands("{}");
  engine.setScene(JSON.stringify(faces), audience, trust);
  const types = [];
  for (let t = 0; t < 30; t++) JSON.parse(engine.feed(JSON.stringify({ t: t * 40, hands: [hand(0.5, 0.6)] }), "desktop")).forEach((e) => types.push(e.type));
  let rejected = false;
  try { engine.setScene('[{"x":3,"y":0.3,"w":0.1}]', "mixed", false); } catch (e) { rejected = true; }
  engine.free();
  return { pointer: types.filter((t) => t === "pointer").length, rejected };
});
process.stdout.write(JSON.stringify(out));
"""


class ShippedModuleTests(unittest.TestCase):

    def test_the_committed_wasm_matches_its_checksum(self):
        digest = hashlib.sha256((WASM_DIR / "hands_core_bg.wasm").read_bytes()).hexdigest()
        self.assertEqual((WASM_DIR / "hands_core_bg.wasm.sha256").read_text().strip(), digest)

    def test_both_display_pages_load_the_local_engine_before_hands(self):
        page = (ROOT / "web" / "display" / "display.html").read_text()
        self.assertLess(page.index("hands/wasm/hands_core.js"), page.index("hands/local.js"))
        self.assertLess(page.index("hands/local.js"), page.index("/static/display/hands.js"))


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class WasmEngineTests(unittest.TestCase):

    def run_node(self, cases):
        done = subprocess.run(["node", "-e", RUNNER, str(WASM_DIR)], input=json.dumps(cases), capture_output=True,
                              text=True, timeout=60, check=True)
        return json.loads(done.stdout)

    def test_only_trusted_hands_drive_the_pointer_in_the_browser(self):
        face = {"x": 0.5, "y": 0.3, "w": 0.1}
        out = self.run_node([{"faces": [], "audience": "authorized", "trust": False},
                             {"faces": [], "audience": "guest_only", "trust": False},
                             {"faces": [{**face, "authorized": True}], "audience": "mixed", "trust": False},
                             {"faces": [{**face, "authorized": False}], "audience": "mixed", "trust": False},
                             {"faces": [], "audience": "empty", "trust": True}])
        self.assertEqual([o["pointer"] > 0 for o in out], [True, False, True, False, False])
        self.assertTrue(all(o["rejected"] for o in out))


class DisplayApiTests(unittest.TestCase):

    def test_faces_carry_no_names_and_need_a_live_authorized_member(self):
        presence = {"people": [
            {"slug": "anna", "known": True, "role": "owner", "confidence": 0.9, "liveness": {"state": "live"},
             "gaze": {"x": 0.4, "y": 0.3}, "raw_proximity": 0.12, "name": "Anna"},
            {"slug": None, "known": False, "gaze": {"x": 0.7, "y": 0.3}, "raw_proximity": 0.1},
            {"slug": "anna", "known": True, "role": "owner", "liveness": {"state": "spoof"}, "gaze": {"x": 0.2, "y": 0.3},
             "raw_proximity": 0.1},
            {"gaze": {"x": 4, "y": 0.3}, "raw_proximity": 0.1}, "junk"]}
        with mock.patch("agenti.desktop.presence_bridge.face_signal",
                        side_effect=lambda p: {"authorized": bool(p.get("known")), "liveness": (p.get("liveness") or {}).get("state", "unknown")}):
            faces = display_api.faces(presence)
        self.assertEqual([f["authorized"] for f in faces], [True, False, False])
        self.assertTrue(all(set(f) == {"x", "y", "w", "authorized"} for f in faces))

    def test_only_semantic_events_are_accepted(self):
        self.assertEqual(display_api.semantic({"type": "action", "action": "volume.up", "hand": "right", "x": 1}),
                         {"type": "action", "action": "volume.up", "hand": "right"})
        for bad in ({"type": "pointer", "x": 0.1}, {"type": "action"}, {"type": "gesture", "gesture": "<script>"},
                    {"type": "gesture", "gesture": {"a": 1}}, "x"):
            self.assertIsNone(display_api.semantic(bad))

    def test_the_scene_is_served_only_to_the_local_display(self):
        request = mock.Mock()
        request.client.host = "192.168.1.20"
        with self.assertRaises(HTTPException):
            asyncio.run(display_api.display_scene(request))

    def test_event_batches_are_bounded(self):
        request = mock.Mock()

        async def body():
            return {"events": [{"type": "action", "action": "volume.up"}] * 33}
        request.json = body
        with mock.patch.object(display_api, "require_display"), self.assertRaises(HTTPException):
            asyncio.run(display_api.display_events(request))


if __name__ == "__main__":
    unittest.main()
