import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from autonomy import memory as memory_module
from autonomy.memory import LocalMemory
from autonomy.router import Router
from autonomy.sync import Sync
from autonomy.vault import KeyFile, Vault
from connection.client import ServerError


def build(folder, key=None):
    return LocalMemory(Vault(Path(folder) / "m.vault", key or Fernet.generate_key()))


class VaultTest(unittest.TestCase):
    def test_data_is_encrypted_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            key = Fernet.generate_key()
            first = build(folder, key)
            first.record("la mia password è hunter2", "ok")
            raw = (Path(folder) / "m.vault").read_bytes()
            self.assertNotIn(b"hunter2", raw)
            self.assertEqual(build(folder, key).recent(5)[0]["text"], "la mia password è hunter2")

    def test_wrong_key_or_tampering_quarantines_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            build(folder).record("a", "b")
            other = build(folder)
            self.assertEqual(other.recent(5), [])
            self.assertTrue((Path(folder) / "m.broken").is_file())
            other.record("c", "d")
            self.assertEqual(len(other.recent(5)), 1)

    def test_key_file_is_sealed_and_stable(self):
        with tempfile.TemporaryDirectory() as folder:
            keys = KeyFile(Path(folder) / "k", lambda b: b[::-1], lambda b: b[::-1])
            first = keys.load()
            self.assertNotEqual((Path(folder) / "k").read_bytes(), first)
            self.assertEqual(keys.load(), first)
            Fernet(first)


class MemoryTest(unittest.TestCase):
    def test_cap_and_text_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            mem = build(folder)
            for i in range(memory_module.MAX_TURNS + 10):
                mem.record(f"t{i}", "r" * 2000)
            turns = mem.recent(10 ** 6)
            self.assertEqual(len(turns), memory_module.MAX_TURNS)
            self.assertEqual(len(turns[-1]["reply"]), memory_module.MAX_TEXT)
            self.assertEqual(turns[-1]["text"], f"t{memory_module.MAX_TURNS + 9}")

    def test_pending_and_forget(self):
        with tempfile.TemporaryDirectory() as folder:
            mem = build(folder)
            a = mem.record("a", "1")
            mem.record("b", "2", synced=True)
            self.assertEqual([t["id"] for t in mem.pending()], [a])
            mem.mark_synced([a])
            self.assertEqual(mem.pending(), [])
            mem.forget()
            self.assertEqual(mem.recent(5), [])

    def test_garbage_entries_are_ignored_on_load(self):
        with tempfile.TemporaryDirectory() as folder:
            key = Fernet.generate_key()
            vault = Vault(Path(folder) / "m.vault", key)
            vault.write({"turns": [{"id": 1}, "x", {"id": "a", "text": "t", "reply": "r"}]})
            self.assertEqual(len(LocalMemory(vault).recent(5)), 1)


class FakeClient:
    def __init__(self, fail=False):
        self.fail, self.sent = fail, []

    def request(self, path, body, **kwargs):
        if self.fail:
            raise ServerError("giu")
        self.sent.append((path, body))
        return {}

    def assist(self, body):
        return {"reply": "dal server"}


class SyncTest(unittest.TestCase):
    def test_pending_turns_go_up_once_the_server_is_back(self):
        with tempfile.TemporaryDirectory() as folder:
            mem = build(folder)
            mem.record("domanda", "risposta")
            down = FakeClient(fail=True)
            self.assertEqual(Sync(down, mem).flush(), 0)
            self.assertEqual(len(mem.pending()), 1)
            up = FakeClient()
            self.assertEqual(Sync(up, mem).flush(), 1)
            self.assertEqual(up.sent[0][0], "/api/nodes/memory-sync")
            self.assertEqual(up.sent[0][1]["turns"][0]["text"], "domanda")
            self.assertEqual(mem.pending(), [])
            self.assertEqual(Sync(up, mem).flush(), 0)


class LocalBrainStub:
    def ready(self):
        return True

    def assist(self, body):
        return {"reply": "locale"}


class RouterMemoryTest(unittest.TestCase):
    def test_local_answers_are_remembered_but_action_followups_are_not(self):
        with tempfile.TemporaryDirectory() as folder:
            mem = build(folder)
            router = Router(FakeClient(), LocalBrainStub(), {"mode": "local"}, False, mem)
            router.assist({"text": "ciao"})
            router.assist({"text": "ciao", "results": [{"ok": True}]})
            self.assertEqual([t["text"] for t in mem.recent(5)], ["ciao"])


if __name__ == "__main__":
    unittest.main()
