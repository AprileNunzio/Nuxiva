import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.nodes import desk_assistant, jev, trust


class JevTest(unittest.IsolatedAsyncioTestCase):
    async def test_fast_planner_retries_without_a_local_token_cap(self):
        with mock.patch.object(desk_assistant, "generate", new_callable=mock.AsyncMock,
                               side_effect=[desk_assistant.BrainUnavailable("fast"), {"reply": "OK"}]) as model:
            result = await desk_assistant.think("Elenca i processi", {}, [], kind="chat")
        self.assertEqual(result["reply"], "OK")
        self.assertEqual([(call.kwargs["kind"], call.kwargs["max_tokens"]) for call in model.await_args_list],
                         [("chat", None), ("deep", None)])

    async def test_only_enrolled_windows_plain_text_can_use_jev(self):
        hp = {"id": "hp-test", "hardware": {"os": "windows"}}
        with (mock.patch.dict("os.environ", {"TYPESAFE_API_KEY": "test-key", "NUXIVA_JEV_WINDOWS_NODES": "hp-test"}),
              mock.patch.object(jev.privacy_gate, "level", return_value="public") as level,
              mock.patch.object(jev.native_core, "symbol") as symbol):
            classify = symbol.return_value
            self.assertEqual(await jev.planner_kind(hp, "Elenca i processi", {"image": "private"}), "deep")
            self.assertEqual(await jev.planner_kind({**hp, "id": "other"}, "Elenca i processi", {}), "deep")
            level.return_value = "personal"
            self.assertEqual(await jev.planner_kind(hp, "Elenca i processi", {}), "deep")
            classify.assert_not_called()
            level.return_value = "public"
            classify.return_value = True
            self.assertEqual(await jev.planner_kind(hp, "Elenca i processi", {}), "chat")
            classify.assert_called_once_with("Elenca i processi", "test-key")
            classify.side_effect = RuntimeError("timeout")
            self.assertEqual(await jev.planner_kind(hp, "Elenca i processi", {}), "deep")


class CleanTest(unittest.TestCase):
    def test_long_workspace_context_and_reply_are_preserved(self):
        content = "a" * 15000 + "fine-contesto"
        self.assertIn("fine-contesto", desk_assistant._prompt("analizza", {"context": {"content": content}}, []))
        self.assertEqual(desk_assistant._clean({"reply": content})["reply"], content)

    def test_new_actions_keep_only_known_fields(self):
        raw = {"reply": "Ecco", "actions": [
            {"type": "run_powershell", "command": "Get-Process", "evil": "x"},
            {"type": "ssh", "host": "nas", "user": "admin", "port": 2222, "command": "uptime"},
            {"type": "ssh", "host": "nas", "user": "admin", "port": 99999, "command": "uptime"},
            {"type": "press_keys", "keys": "ctrl+s"},
            {"type": "window", "op": "minimize", "title": "Word"},
            {"type": "format_disk", "path": "C:"}]}
        out = desk_assistant._clean(raw)
        types = [a["type"] for a in out["actions"]]
        self.assertEqual(types, ["run_powershell", "ssh", "ssh", "press_keys", "window"])
        self.assertNotIn("evil", out["actions"][0])
        self.assertEqual(out["actions"][1]["port"], 2222)
        self.assertNotIn("port", out["actions"][2])
        self.assertTrue(out["followup"])

    def test_permissions_reach_the_model_and_forbidden_ones_are_marked(self):
        body = {"env": {"permissions": {"shell.powershell": "deny", "files.create": "allow", "remote.ssh": "ask"}},
                "context": {}}
        prompt = desk_assistant._prompt("crea un file", body, [])
        self.assertIn("shell.powershell=VIETATO", prompt)
        self.assertIn("files.create=consentito", prompt)
        self.assertIn("remote.ssh=chiedi conferma", prompt)


class TrustTest(unittest.TestCase):
    def test_fingerprint_of_the_local_authority(self):
        pem = ("-----BEGIN CERTIFICATE-----\nMAA=\n-----END CERTIFICATE-----\n")
        with tempfile.TemporaryDirectory() as tmp:
            ca = Path(tmp) / "ca.pem"
            with mock.patch.object(trust, "CA_FILE", ca):
                self.assertEqual(trust.ca_fingerprint(), "")
                ca.write_text(pem, encoding="ascii")
                value = trust.ca_fingerprint()
        self.assertRegex(value, r"^[0-9A-F]{4}(-[0-9A-F]{4}){3}$")


class ResearchTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_url_open_returns_a_typed_action_without_a_model(self):
        with mock.patch.object(desk_assistant, "generate", new_callable=mock.AsyncMock) as model:
            result = await desk_assistant.assist({"id": "pc"}, {"text": "Apri https://example.com/guida"})
        model.assert_not_awaited()
        self.assertEqual(result["actions"], [{"type": "open_url", "url": "https://example.com/guida"}])

    async def test_explicit_research_uses_only_the_question_and_returns_no_actions(self):
        with (
            mock.patch("agenti.research.service.research", new_callable=mock.AsyncMock) as search,
            mock.patch("agenti.research.report.render", return_value="Sources"),
        ):
            result = await desk_assistant.assist({"id": "pc"}, {
                "text": "Cerca online: come si usa Excel?",
                "context": {"content": "private document"},
            })
        search.assert_awaited_once_with("come si usa Excel?")
        self.assertEqual(result["show"], "Sources")
        self.assertEqual(result["actions"], [])


if __name__ == "__main__":
    unittest.main()
