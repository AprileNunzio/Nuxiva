import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "display"


class StageFitTest(unittest.TestCase):
    def setUp(self):
        self.css = (WEB / "display.css").read_text(encoding="utf-8")
        self.fit = (WEB / "stage_fit.js").read_text(encoding="utf-8")

    def test_stage_never_scrolls(self):
        rule = re.search(r"\.stage-body \{[^}]*\}", self.css).group(0)
        self.assertIn("overflow: hidden", rule)
        self.assertNotIn("overflow: auto", rule)
        weather = (WEB / "weather.css").read_text(encoding="utf-8")
        self.assertNotIn("overflow-x: auto", weather)
        self.assertNotIn("min-width:${", (WEB / "weather_charts.js").read_text(encoding="utf-8"))

    def test_fit_order_wide_then_voice_then_priority_then_scale(self):
        for token in ('body.classList.add("stage-wide")', 'D.setVoiceOnly(on, "stage")', "fit-cut", 'setProperty("--fit"'):
            self.assertIn(token, self.fit)
        self.assertLess(self.fit.index('classList.add("stage-wide")'), self.fit.index("cut(level)"))
        self.assertIn("zoom: var(--fit)", self.css)
        self.assertIn("body.stage-wide .stage", self.css)

    def test_voice_only_keeps_reasons_apart(self):
        strip = (WEB / "voice_strip.js").read_text(encoding="utf-8")
        self.assertIn('reason = "desk"', strip)
        self.assertIn("reasons.size > 0", strip)

    def test_loaded_after_stage_and_voice_strip(self):
        html = (WEB / "display.html").read_text(encoding="utf-8")
        position = html.index("/static/display/stage_fit.js")
        self.assertGreater(position, html.index("/static/display/stage.js"))
        self.assertGreater(position, html.index("/static/display/voice_strip.js"))

    def test_weather_sections_declare_priority(self):
        weather = (WEB / "weather.js").read_text(encoding="utf-8")
        self.assertIn('data-prio="${PRIO[cls] || 2}"', weather)
        self.assertGreaterEqual(weather.count('data-prio="'), 5)


if __name__ == "__main__":
    unittest.main()
