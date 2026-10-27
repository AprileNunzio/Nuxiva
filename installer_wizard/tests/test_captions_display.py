import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "display"

HARNESS = r"""
const fs = require("fs");
class El {
  constructor(tag) { this.tag = tag; this.children = []; this.style = { props: {}, setProperty(k, v) { this.props[k] = v; } };
    this.dataset = {}; this.hidden = false; this.textContent = ""; this._cls = new Set(); this.attrs = {}; this.removed = false;
    const self = this; this.classList = { add: (c) => self._cls.add(c), remove: (c) => self._cls.delete(c),
      toggle: (c, on) => { if (on === undefined) on = !self._cls.has(c); on ? self._cls.add(c) : self._cls.delete(c); return on; }, contains: (c) => self._cls.has(c) };
    Object.defineProperty(this, "className", { get: () => [...self._cls].join(" "), set: (v) => { self._cls = new Set(String(v).split(/\s+/).filter(Boolean)); } }); }
  set id(v) { this._id = v; } get id() { return this._id; }
  setAttribute(k, v) { this.attrs[k] = v; }
  append(...n) { n.forEach((c) => this.appendChild(c)); }
  appendChild(c) { this.children.push(c); c.parent = this; return c; }
  remove() { this.removed = true; if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); }
}
const body = new El("body");
global.document = { body, createElement: (t) => new El(t) };
global.window = { NuxivaDisplay: {}, addEventListener() {}, PageText: { scope: () => (k) => k, onChange() {} } };
global.PageText = window.PageText;
global.fetch = async () => ({ ok: true, json: async () => CONFIG });
global.setInterval = () => 0;
const timers = [];
global.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
global.clearTimeout = () => {};
global.CONFIG = JSON.parse(process.argv[3]);
eval(fs.readFileSync(process.argv[2], "utf8"));
const caps = window.NuxivaDisplay.Captions;
const root = body.children[0];
const text = () => root.children.map((line) => line.children[1].children.map((w) => w.textContent).join("").trim());
const out = {};
const g = (fn, d = null) => { try { return fn(); } catch (e) { return d; } };
(async () => {
  await caps.reload();
  caps.event({ type: "ready", voiceprint: true });
  caps.event({ type: "partial", utt: "a1", seq: 1, text: "accendi la", stable: 0, speaker: "anna", addressed: true });
  caps.event({ type: "partial", utt: "a1", seq: 2, text: "accendi la luce", stable: 2, speaker: "anna", addressed: true });
  out.partial = text();
  out.stable = g(() => root.children[0].children[1].children.map((w) => w.classList.contains("stable")));
  out.who = g(() => root.children[0].children[0].textContent);
  out.hue = g(() => root.children[0].style.props["--cap-hue"]);
  caps.event({ type: "partial", utt: "x", seq: 1, text: "<img src=x onerror=alert(1)>", stable: 0, speaker: "../../etc", addressed: true });
  out.safe = g(() => root.children[1].children[1].children[0].textContent);
  out.safeWho = g(() => root.children[1].children[0].hidden);
  caps.event({ type: "transcript", utt: "a1", text: "accendi la luce del salotto", speaker: "anna" });
  out.final = g(() => root.children[0].children[1].children.map((w) => w.textContent).join("").trim());
  out.done = g(() => root.children[0].classList.contains("done"));
  caps.event({ type: "heard", utt: "h1", text: "che bella giornata", speaker: null });
  const heard = root.children.find((c) => c.children[1].children[0] && c.children[1].children[0].textContent.startsWith("che"));
  out.heardWho = heard ? heard.children[0].textContent : null;
  out.heardAddressed = heard ? heard.classList.contains("addressed") : null;
  caps.event({ type: "caption_drop", utt: "x" });
  out.dropped = root.children.every((c) => !c.children[1].children[0] || c.children[1].children[0].textContent !== "<img");
  for (let i = 0; i < 6; i++) caps.event({ type: "heard", utt: "m" + i, text: "frase " + i });
  out.max = root.children.filter((c) => !c.classList.contains("out")).length;
  out.cfg = { size: root.dataset.size, position: root.dataset.position, hidden: root.hidden, has: body.classList.contains("has-captions") };
  console.log(JSON.stringify(out));
})();
"""


def run(config: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "run.cjs"
        script.write_text(HARNESS)
        done = subprocess.run(["node", str(script), str(WEB / "captions.js"), json.dumps(config)], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout.strip().splitlines()[-1])


@unittest.skipUnless(shutil.which("node"), "node assente")
class CaptionsTest(unittest.TestCase):
    def test_live_words_speaker_and_final_text(self):
        out = run({"captions": {"enabled": True, "scope": "all", "speaker": True, "size": "large", "hold": 4, "position": "center"},
                   "speakers": {"anna": "Anna Rossi"}})
        self.assertEqual(out["partial"][0], "accendi la luce")
        self.assertEqual(out["stable"], [True, True, False])
        self.assertEqual(out["who"], "Anna Rossi")
        self.assertTrue(out["hue"].isdigit())
        self.assertEqual(out["final"], "accendi la luce del salotto")
        self.assertTrue(out["done"])
        self.assertEqual(out["cfg"], {"size": "large", "position": "center", "hidden": False, "has": True})

    def test_transcript_text_is_never_interpreted_as_markup(self):
        out = run({"captions": {}, "speakers": {}})
        self.assertEqual(out["safe"], "<img ")
        self.assertTrue(out["safeWho"])
        self.assertTrue(out["dropped"])

    def test_unaddressed_speech_gets_unknown_label_and_lines_are_capped(self):
        out = run({"captions": {}, "speakers": {}})
        self.assertEqual(out["heardWho"], "cap_unknown")
        self.assertFalse(out["heardAddressed"])
        self.assertLessEqual(out["max"], 3)

    def test_addressed_scope_hides_room_conversations(self):
        out = run({"captions": {"scope": "addressed"}, "speakers": {}})
        self.assertIsNone(out["heardWho"])

    def test_disabled_captions_show_nothing(self):
        out = run({"captions": {"enabled": False}, "speakers": {}})
        self.assertEqual(out["partial"], [])
        self.assertTrue(out["cfg"]["hidden"])
        self.assertFalse(out["cfg"]["has"])


class CaptionsSourceTest(unittest.TestCase):
    def test_captions_have_no_box_and_never_use_inner_html(self):
        css = (WEB / "captions.css").read_text()
        self.assertNotIn("backdrop-filter", css)
        self.assertNotIn("border:", css.replace("border-radius", ""))
        self.assertNotIn("innerHTML", (WEB / "captions.js").read_text())

    def test_page_loads_captions_before_the_ear(self):
        html = (WEB / "display.html").read_text()
        self.assertLess(html.index("captions.js"), html.index("ear.js"))
        self.assertIn("captions.css", html)

    def test_ear_forwards_events_to_captions(self):
        self.assertIn("D.Captions.event(ev)", (WEB / "ear.js").read_text())

    def test_captions_layer_above_3d_avatar(self):
        captions_css = (WEB / "captions.css").read_text()
        display_css = (WEB / "display.css").read_text()
        self.assertIn("z-index: 25;", captions_css)
        self.assertIn(".caption { position: absolute; left: 50%; bottom: 128px; transform: translateX(-50%); width: min(920px, 90vw); text-align: center; transition: opacity 0.5s; z-index: 25; }", display_css)
        self.assertIn("#core { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 20;", display_css)


if __name__ == "__main__":
    unittest.main()
