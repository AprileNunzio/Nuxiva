import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from agenti.firewall import model
from agenti.firewall.defense import responses, view
from agenti.firewall.defense.guardian import guardian
from agenti.firewall.store import store
from tests.test_firewall_runtime import FirewallBase

WIDGETS = Path(__file__).resolve().parents[1] / "agenti" / "sicurezza" / "firewall" / "widget"
HARNESS = """
const fs = require("fs");
let widget;
global.NuxivaDesk = { register: (id, impl) => { widget = impl; } };
global.document = { documentElement: { lang: "it" } };
eval(fs.readFileSync(process.argv[2], "utf8"));
const dict = JSON.parse(fs.readFileSync(process.argv[3], "utf8")).dictionary;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
const ctx = {
  esc, arr: (v, n) => (Array.isArray(v) ? v.slice(0, n) : []), num: (v) => (Number.isFinite(Number(v)) ? Number(v) : 0),
  str: (v, n) => String(v ?? "").slice(0, n), now: () => 1000,
  t: (k, p = {}) => (dict[k] ?? k).replace(/{{(\\w+)}}/g, (_, x) => p[x]),
  count: (k, n) => (dict[k + (n === 1 ? "_one" : "_other")] ?? k).replace("{{n}}", n),
  head: (o) => `<h4>${esc(o.label)}</h4>`, empty: (s) => `<p class="empty">${esc(s)}</p>`, icon: () => "<i></i>",
};
const el = { dataset: {}, innerHTML: "" };
widget.render(el, JSON.parse(process.argv[4]), ctx);
process.stdout.write(el.innerHTML);
"""


def render(widget, lang, data):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(HARNESS)
    try:
        out = subprocess.run(["node", handle.name, str(WIDGETS / widget / "widget.js"), str(WIDGETS / widget / "language" / f"{lang}.json"),
                              json.dumps(data)], capture_output=True, text=True, timeout=20)
    finally:
        Path(handle.name).unlink()
    assert out.returncode == 0, out.stderr
    return out.stdout


class ViewTests(FirewallBase):

    def test_calm_hides_the_automatic_card_but_the_provider_answers(self):
        guardian.assessment = {"posture": "calm", "incidents": [], "actions": [], "countries": [], "internet": 0, "lan": 0, "at": 1.0}
        self.assertIsNone(view.notable())
        self.assertEqual(view.build()["posture"], "calm")

    def test_attack_view_is_compact_and_has_no_raw_internals(self):
        now = time.time()
        store.policy = model.policy({"mode": "protect"})
        store.responses["tarpit:203.0.113.9"] = responses.build("tarpit", "203.0.113.9", 10)
        guardian.evaluate([{"kind": "brute_force", "severity": "critical", "src": "198.51.100.7", "dst": "192.168.1.10", "count": 9, "at": now}],
                          set(), now)
        data = view.notable()
        self.assertEqual(data["posture"], "attack")
        self.assertEqual(data["defenses"][0]["kind"], "tarpit")
        self.assertEqual(set(data["incidents"][0]), {"id", "kind", "kinds", "stage", "level", "country", "origin", "src", "targets", "last_at"})
        self.assertNotIn("journal", data)


@unittest.skipUnless(shutil.which("node"), "node assente")
class WidgetRender(unittest.TestCase):

    def test_status_speaks_plainly_in_every_language(self):
        for lang in ("it", "en", "fr", "es"):
            html = render("defense_status", lang, {"posture": "attack", "mode": "protect", "defenses": [{"kind": "block"}]})
            dictionary = json.loads((WIDGETS / "defense_status" / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            self.assertIn(dictionary["p_attack"], html)
            self.assertIn(dictionary["h_attack"].replace("'", "&#39;"), html)

    def test_monitor_mode_is_explained(self):
        html = render("defense_status", "it", {"posture": "alert", "mode": "monitor"})
        self.assertIn("sta solo osservando", html)

    def test_incidents_show_country_and_defences_and_escape_text(self):
        data = {"incidents": [{"kind": "brute_force", "country": "CN", "origin": "internet", "level": "high", "src": "<x>"},
                              {"kind": "<script>", "country": "", "origin": "lan", "level": "weird"}],
                "defenses": [{"kind": "tarpit", "expires": 1000 + 600}, {"kind": "<i>", "expires": 5}]}
        html = render("defense_incidents", "it", data)
        self.assertIn("Tentativi di indovinare una password", html)
        self.assertIn("🇨🇳", html)
        self.assertIn("da un dispositivo di casa", html)
        self.assertIn("Tentativi rallentati", html)
        self.assertIn("per 10 min", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<x>", html)
        self.assertNotIn("<i>", html)

    def test_empty_state(self):
        self.assertIn("Nessun tentativo di intrusione", render("defense_incidents", "it", {}))

    def test_languages_have_the_same_keys(self):
        for wid in ("defense_status", "defense_incidents"):
            keys = [set(json.loads((WIDGETS / wid / "language" / f"{l}.json").read_text(encoding="utf-8"))["dictionary"]) for l in ("it", "en", "fr", "es")]
            self.assertTrue(all(k == keys[0] for k in keys), wid)


if __name__ == "__main__":
    unittest.main()
