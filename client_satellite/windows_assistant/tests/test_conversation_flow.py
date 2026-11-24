import importlib
import sys
import threading
import types
import unittest
from unittest import mock

from i18n.strings import t
from permissions.gate import Denied


class CaptureError(RuntimeError):
    pass


def _stubs():
    capture = types.ModuleType("senses.capture")
    capture.CaptureError = CaptureError
    capture.webcam_image = mock.Mock(return_value=b"jpeg")
    capture.window_image = mock.Mock(return_value=b"jpeg")
    reading = types.ModuleType("senses.reading")
    reading.window_text = mock.Mock(return_value="")
    windows = types.ModuleType("senses.windows")
    windows.Focus = object
    package = types.ModuleType("senses")
    package.__path__ = []
    package.capture, package.reading, package.windows = capture, reading, windows
    executor = types.ModuleType("actions.executor")
    executor.Executor = object
    return {"senses": package, "senses.capture": capture, "senses.reading": reading, "senses.windows": windows,
            "actions.executor": executor}


class Dispatch:
    def post(self, fn, *args):
        fn(*args)

    def call(self, fn, *args):
        return fn(*args)


class UI:
    def __init__(self):
        self.dispatch, self.said, self.notes, self.states = Dispatch(), [], [], []

    def show_panel(self):
        self.states.append("shown")

    def hide_panel(self):
        self.states.append("hidden")

    def say(self, who, text, show=None):
        self.said.append((who, text))

    def note(self, text):
        self.notes.append(text)

    def set_state(self, state):
        self.states.append(state)


class Executor:
    def __init__(self, results=None):
        self.calls, self.results = [], results

    def run(self, actions):
        self.calls.append(actions)
        results = self.results or [{"type": a["type"], "ok": True, **{k: v for k, v in a.items() if k != "type"},
                                    "browser": "Google Chrome" if a.get("browser") else ""} for a in actions]
        return [], results


class Gate:
    def __init__(self, deny=False):
        self.requests, self.deny = [], deny

    def check(self, request, always_ask=False):
        self.requests.append((request.capability, always_ask))
        if self.deny:
            raise Denied("Non autorizzato")


class Focus:
    def current(self):
        return None


class Backend:
    def __init__(self, *answers):
        self.answers, self.bodies = list(answers), []

    def assist(self, body):
        self.bodies.append(dict(body))
        return self.answers.pop(0)


class ConversationFlowTest(unittest.TestCase):
    def setUp(self):
        self.modules = mock.patch.dict(sys.modules, _stubs())
        self.modules.start()
        sys.modules.pop("app.conversation", None)
        self.conversation = importlib.import_module("app.conversation")
        self.capture = sys.modules["senses.capture"]

    def tearDown(self):
        sys.modules.pop("app.conversation", None)
        self.modules.stop()

    def _run(self, text, backend, executor=None, gate=None, screenshots=None):
        ui, executor, gate = UI(), executor or Executor(), gate or Gate()
        policy = mock.Mock(summary=mock.Mock(return_value={}))
        voice = mock.Mock()
        conv = self.conversation.Conversation(backend, executor, gate, policy, Focus(), ui, voice, lambda: {},
                                              screenshots=screenshots)
        conv.busy = threading.Lock()
        conv._ask(text, "it", False)
        return ui, executor, gate

    def test_open_site_in_chrome_runs_without_brain_or_webcam(self):
        backend = Backend()
        ui, executor, gate = self._run("aprimi il sito nunziotech.com su google chrome", backend)
        self.assertEqual(backend.bodies, [])
        self.assertEqual(executor.calls, [[{"type": "open_url", "url": "https://nunziotech.com", "browser": "chrome"}]])
        self.capture.webcam_image.assert_not_called()
        self.assertEqual(ui.said[-1], ("nuxiva", t("report.site_opened_in", url="https://nunziotech.com",
                                                    browser="Google Chrome")))

    def test_spoken_screenshot_hides_the_panel_and_saves_without_brain(self):
        from screenshot.service import Outcome
        backend = Backend()
        shots = mock.Mock()
        shots.shoot.return_value = Outcome("delivered", "screenshot.saved", "ok", {"name": "pc.png", "folder": "\\\\nas"})
        shots.message.return_value = "salvato"
        with mock.patch.object(self.conversation, "HIDE_DELAY", 0):
            ui, executor, gate = self._run("fai uno screenshot di quello che vedi", backend, screenshots=shots)
        self.assertEqual(backend.bodies, [])
        self.assertEqual(ui.states[:2], ["hidden", "shown"])
        shots.shoot.assert_called_once_with()
        self.capture.window_image.assert_not_called()
        self.assertEqual(gate.requests, [])
        self.assertEqual(ui.said[-1], ("nuxiva", t("screenshot.voice_saved")))

    def test_model_cannot_open_the_webcam_without_an_explicit_request(self):
        backend = Backend({"need": "webcam", "actions": []})
        ui, executor, gate = self._run("dimmi qualcosa di carino", backend)
        self.capture.webcam_image.assert_not_called()
        self.assertNotIn("senses.webcam", [c for c, _ in gate.requests])
        self.assertEqual(ui.said[-1], ("nuxiva", t("senses.webcam.not_requested")))

    def test_explicit_webcam_request_still_works(self):
        backend = Backend({"reply": "Ti vedo", "actions": []})
        ui, _, gate = self._run("guardami dalla webcam", backend)
        self.capture.webcam_image.assert_called_once()
        self.assertIn(("senses.webcam", False), gate.requests)
        self.assertEqual(backend.bodies[0]["image_source"], "webcam")

    def test_screen_requested_only_by_the_model_always_asks(self):
        backend = Backend({"need": "screen", "actions": []}, {"reply": "Vedo", "actions": []})
        _, _, gate = self._run("come procedo?", backend)
        self.assertIn(("senses.screen", True), gate.requests)

    def test_brain_unavailable_is_translated(self):
        backend = Backend({"error": "brain_unavailable", "reply": "", "actions": []})
        ui, _, _ = self._run("bene grazie e a te?", backend)
        self.assertEqual(ui.said[-1], ("nuxiva", t("brain.unavailable")))
        self.assertEqual(ui.states[-1], "error")

    def test_reply_never_claims_a_failed_action(self):
        backend = Backend({"reply": "Ho aperto il browser", "actions": [{"type": "open_url", "url": "https://x.it"}]})
        executor = Executor([{"type": "open_url", "ok": False, "error": "non autorizzato"}])
        ui, _, _ = self._run("fai una cosa sul pc", backend, executor)
        self.assertEqual(ui.said[-1], ("nuxiva", t("report.failed", detail="non autorizzato")))


if __name__ == "__main__":
    unittest.main()
