import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "display"


class AvatarSpaceTest(unittest.TestCase):
    def test_avatar_moves_only_when_widgets_cover_it(self):
        desk = (WEB / "desk.js").read_text(encoding="utf-8")
        self.assertIn("if (!takeover && zone && !covers(normal.concat(pinned), W, H)) zone = null;", desk)
        self.assertNotIn("!blocked.length && !covers", desk)
        self.assertIn("voice: true", desk)

    def test_voice_only_mode_is_wired(self):
        html = (WEB / "display.html").read_text(encoding="utf-8")
        self.assertLess(html.index("/static/display/look.js"), html.index("/static/display/voice_strip.js"))
        self.assertIn("D.setVoiceOnly", (WEB / "look.js").read_text(encoding="utf-8"))
        css = (WEB / "display.css").read_text(encoding="utf-8")
        self.assertIn("body.voice-only #core, body.voice-only #scene", css)
        self.assertIn("prefers-reduced-motion", (WEB / "voice_strip.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
