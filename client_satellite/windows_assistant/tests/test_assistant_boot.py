import contextlib
import ctypes
import importlib
import importlib.abc
import importlib.machinery
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

OPTIONAL = ("keyboard", "tkinter", "customtkinter", "sounddevice", "uiautomation", "mss", "cv2", "pyperclip", "pystray", "comtypes", "winreg", "msvcrt", "winsound", "win32api", "win32con", "win32gui", "wmi")


class _Stub(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, roots):
        self.roots = roots

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.roots:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        module = mock.MagicMock(name=spec.name)
        module.__path__ = []
        module.__spec__ = spec
        module.__name__ = spec.name
        return module

    def exec_module(self, module):
        return None


def _missing():
    gone = []
    for name in OPTIONAL:
        try:
            importlib.import_module(name)
        except ImportError:
            gone.append(name)
    return gone


class BootTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = _Stub(_missing())
        sys.meta_path.insert(0, cls.stub)
        cls.patches = []
        for attribute, value in (("windll", mock.MagicMock()), ("WINFUNCTYPE", ctypes.CFUNCTYPE),
                                 ("WinDLL", mock.MagicMock()), ("WinError", OSError)):
            if not hasattr(ctypes, attribute):
                patch = mock.patch.object(ctypes, attribute, value, create=True)
                patch.start()
                cls.patches.append(patch)
        for name in list(sys.modules):
            if name.split(".")[0] in cls.stub.roots:
                del sys.modules[name]

    @classmethod
    def tearDownClass(cls):
        sys.meta_path.remove(cls.stub)
        for patch in cls.patches:
            patch.stop()
        for name in list(sys.modules):
            if name.split(".")[0] in cls.stub.roots or name == "app.assistant":
                del sys.modules[name]

    def test_assistant_builds_and_wires_every_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            from settings import paths, protect
            patches = [mock.patch.object(paths, "DATA_DIR", data)]
            for name in ("CONFIG_FILE", "PERMISSIONS_FILE", "KEY_FILE", "LOG_FILE", "BACKUP_DIR"):
                patches.append(mock.patch.object(paths, name, data / name.lower()))
            if sys.platform != "win32":
                patches.append(mock.patch.object(protect, "seal", lambda value: value))
                patches.append(mock.patch.object(protect, "unseal", lambda value: value))
            with contextlib.ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                assistant_module = importlib.import_module("app.assistant")
                real_policy = assistant_module.Policy
                stack.enter_context(mock.patch.object(
                    assistant_module, "Policy", lambda: real_policy(data / "permissions.json")))
                cfg = {"server": "https://127.0.0.1:8443", "node_id": "n1", "token": "t", "ca": "", "pin": "",
                       "key": "", "hotkey": "ctrl+alt+n", "voice": True, "agent_name": ""}
                with mock.patch.object(assistant_module, "Interface") as interface, \
                        mock.patch.object(assistant_module, "Voice") as voice:
                    voice.return_value.has_server = False
                    built = assistant_module.Assistant(cfg)
                    actions = interface.call_args.args[1]
                    for name in ("ask", "listen", "stop", "quit", "is_muted", "mute", "save", "autostart", "fingerprint",
                                 "settings_saved", "unpair", "policy", "permissions_changed", "widgets", "models",
                                 "hardware"):
                        self.assertIn(name, actions)
                    actions["stop"]()
                    self.assertIs(actions["policy"](), built.policy)
                    for attribute in ("conversation", "heartbeat", "compute", "inbox", "backup", "updater", "router",
                                      "brain", "memory"):
                        self.assertTrue(hasattr(built, attribute), attribute)


if __name__ == "__main__":
    unittest.main()
