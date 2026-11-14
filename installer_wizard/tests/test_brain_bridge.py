import unittest
from unittest import mock

from agenti.mcpclient import brain


class FakeBrain:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def dispatch(self, text, principal, now_ms):
        self.calls.append((text, principal, now_ms))
        if self.error:
            raise ValueError(self.error)
        return self.reply

    def cancel(self):
        self.calls.append("cancel")


class BrainBridgeTests(unittest.TestCase):
    def tearDown(self):
        brain._brain = None

    def test_disabled_by_default(self):
        with mock.patch.object(brain, "env_get", return_value="off"):
            self.assertFalse(brain.enabled())
            self.assertIsNone(brain.dispatch("accendi", "nunzio", 1))

    def test_dispatch_returns_parsed_reply(self):
        fake = FakeBrain(reply='{"kind": "conversation"}')
        brain._brain = fake
        with mock.patch.object(brain, "env_get", return_value="rust"):
            self.assertEqual(brain.dispatch("ciao", None, 5), {"kind": "conversation"})
        self.assertEqual(fake.calls, [("ciao", "guest", 5)])

    def test_rejection_is_reported_not_swallowed(self):
        brain._brain = FakeBrain(error="brain.dispatch.x")
        with mock.patch.object(brain, "env_get", return_value="rust"):
            self.assertEqual(brain.dispatch("ciao", "nunzio", 5), {"kind": "rejected", "error": "brain.dispatch.x"})

    def test_hostile_text_is_dropped(self):
        brain._brain = FakeBrain(reply="{}")
        with mock.patch.object(brain, "env_get", return_value="rust"):
            self.assertIsNone(brain.dispatch("", "nunzio", 1))
            self.assertIsNone(brain.dispatch("a" * 9000, "nunzio", 1))
            self.assertIsNone(brain.dispatch(None, "nunzio", 1))

    def test_missing_native_module_gives_none(self):
        with mock.patch.object(brain, "env_get", return_value="rust"), mock.patch.object(brain.native_core, "symbol", return_value=None):
            self.assertIsNone(brain.dispatch("ciao", "nunzio", 1))

    def test_reset_cancels_running_work(self):
        fake = FakeBrain(reply="{}")
        brain._brain = fake
        brain.reset()
        self.assertEqual(fake.calls, ["cancel"])
        self.assertIsNone(brain._brain)


if __name__ == "__main__":
    unittest.main()
