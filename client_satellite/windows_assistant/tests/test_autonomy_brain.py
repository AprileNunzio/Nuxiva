import json
import unittest
from unittest import mock

from autonomy import brain, catalog, profile
from autonomy.router import Router
from connection.client import ServerError


class FakeProbe:
    def __init__(self, models=("qwen3:4b",), up=True):
        self.models, self.up = models, up

    def read(self):
        return {"available": self.up, "version": "x", "models": [{"name": m, "size_gb": 1} for m in self.models],
                "running": []}


TIER = profile.TIERS[3]


class HostTest(unittest.TestCase):
    def test_second_server_is_opt_in_and_never_in_local_only(self):
        self.assertFalse(profile.host_full({}))
        self.assertTrue(profile.host_full({"host_full": True, "mode": "auto"}))
        self.assertTrue(profile.host_full({"host_full": True, "mode": "server"}))
        self.assertFalse(profile.host_full({"host_full": True, "mode": "local"}))


class CatalogTest(unittest.TestCase):
    def test_unknown_types_and_fields_are_dropped(self):
        clean = catalog.sanitize([
            {"type": "create_folder", "path": "C:/x", "evil": "1"},
            {"type": "format_disk", "path": "C:"},
            {"type": "open_url", "url": 5},
            "no",
        ])
        self.assertEqual(clean, [{"type": "create_folder", "path": "C:/x"}, {"type": "open_url"}])

    def test_only_allowed_actions_survive_and_count_is_capped(self):
        many = [{"type": "show_desktop"}] * 10
        self.assertEqual(len(catalog.sanitize(many)), catalog.MAX_ACTIONS)
        self.assertEqual(catalog.sanitize(many, {"open_url"}), [])

    def test_lists_are_kept_as_strings_only(self):
        clean = catalog.sanitize([{"type": "create_docx", "path": "a.docx", "paragraphs": ["a", 3, "b"]}])
        self.assertEqual(clean[0]["paragraphs"], ["a", "b"])

    def test_limits(self):
        clean = catalog.sanitize([{"type": "type_text", "text": "x" * (catalog.MAX_TEXT + 5)}])
        self.assertEqual(len(clean[0]["text"]), catalog.MAX_TEXT)


class ParseTest(unittest.TestCase):
    def test_valid_json(self):
        out = brain.parse(json.dumps({"reply": "Fatto", "actions": [{"type": "show_desktop"}], "followup": True}))
        self.assertEqual(out, {"reply": "Fatto", "actions": [{"type": "show_desktop"}], "followup": True})

    def test_followup_needs_actions(self):
        self.assertFalse(brain.parse('{"reply":"ok","followup":true}')["followup"])

    def test_plain_text_becomes_a_reply(self):
        self.assertEqual(brain.parse("ciao")["reply"], "ciao")
        self.assertEqual(brain.parse("[1]")["actions"], [])


class LocalBrainTest(unittest.TestCase):
    def test_model_selection_and_readiness(self):
        self.assertTrue(brain.LocalBrain(FakeProbe(), {}, TIER).ready())
        self.assertFalse(brain.LocalBrain(FakeProbe(up=False), {}, TIER).ready())
        self.assertFalse(brain.LocalBrain(FakeProbe(models=("mistral:7b",)), {}, TIER).ready())
        self.assertEqual(brain.LocalBrain(FakeProbe(models=("a:1", "qwen3:4b")), {"local_model": "a:1"}, TIER).model(), "a:1")

    def test_assist_builds_a_safe_request_and_keeps_history(self):
        sent = {}

        def fake_post(path, payload):
            sent.update(path=path, payload=payload)
            return {"message": {"content": json.dumps({"reply": "Apro", "actions": [{"type": "open_app", "name": "Note"}],
                                                       "followup": False})}}

        local = brain.LocalBrain(FakeProbe(), {"agent_name": "Aria"}, TIER)
        body = {"text": "apri note", "lang": "it", "env": {"actions": ["open_app"]}, "context": {"window": "Excel"}}
        with mock.patch.object(brain, "_post", fake_post):
            result = local.assist(body)
        self.assertEqual(result["actions"], [{"type": "open_app", "name": "Note"}])
        self.assertTrue(result["local"])
        self.assertEqual(sent["path"], "/api/chat")
        self.assertFalse(sent["payload"]["stream"])
        self.assertIn("Aria", sent["payload"]["messages"][0]["content"])
        self.assertIn("open_app", sent["payload"]["messages"][0]["content"])
        self.assertNotIn("run_powershell", sent["payload"]["messages"][0]["content"])
        self.assertEqual(len(local.history), 2)

    def test_disallowed_action_from_the_model_is_removed(self):
        def fake_post(path, payload):
            return {"message": {"content": json.dumps({"reply": "x", "actions": [{"type": "run_powershell",
                                                                                   "command": "del *"}]})}}

        local = brain.LocalBrain(FakeProbe(), {}, TIER)
        with mock.patch.object(brain, "_post", fake_post):
            result = local.assist({"text": "x", "env": {"actions": ["open_app"]}})
        self.assertEqual(result["actions"], [])

    def test_no_model_raises(self):
        with self.assertRaises(brain.BrainError):
            brain.LocalBrain(FakeProbe(up=False), {}, TIER).assist({"text": "x"})


class FakeClient:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    def assist(self, body):
        self.calls += 1
        if self.fail:
            raise ServerError("giu")
        return {"reply": "server"}


class FakeBrain:
    def __init__(self, ready=True):
        self._ready = ready

    def ready(self):
        return self._ready

    def assist(self, body):
        return {"reply": "locale"}


class RouterTest(unittest.TestCase):
    def router(self, mode, client, brain_ready=True, has_server=True):
        return Router(client, FakeBrain(brain_ready), {"mode": mode}, has_server)

    def test_auto_prefers_the_server(self):
        client = FakeClient()
        self.assertEqual(self.router("auto", client).assist({})["reply"], "server")

    def test_auto_falls_back_and_stops_retrying_for_a_while(self):
        client = FakeClient(fail=True)
        router = self.router("auto", client)
        self.assertEqual(router.assist({})["reply"], "locale")
        self.assertEqual(router.assist({})["reply"], "locale")
        self.assertEqual(client.calls, 1)

    def test_server_only_never_uses_local(self):
        with self.assertRaises(ServerError):
            self.router("server", FakeClient(fail=True)).assist({})

    def test_local_only_never_calls_the_server(self):
        client = FakeClient()
        self.assertEqual(self.router("local", client).assist({})["reply"], "locale")
        self.assertEqual(client.calls, 0)

    def test_no_server_no_model_explains(self):
        with self.assertRaises(ServerError):
            self.router("auto", FakeClient(), brain_ready=False, has_server=False).assist({})

    def test_auto_without_local_model_reports_the_server_error(self):
        with self.assertRaises(ServerError):
            self.router("auto", FakeClient(fail=True), brain_ready=False).assist({})


if __name__ == "__main__":
    unittest.main()
