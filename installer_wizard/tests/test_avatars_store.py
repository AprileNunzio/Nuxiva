import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.avatars import api, store


class AvatarStoreTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        patches = [mock.patch.object(store, "ROOT", self.root), mock.patch.object(store, "ACTIVE_FILE", self.root / "active.txt")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_upload_rejects_traversal_and_bad_types(self):
        for name, filename in (("../x", "a.glb"), ("ok", "shell.sh"), ("ok", ".hidden.glb"), ("ok", "..")):
            with self.assertRaises(store.AvatarError):
                store.save(name, filename, io.BytesIO(b"x"))
        store.save("ok", "../../evil.glb", io.BytesIO(b"x"))
        self.assertEqual([p.relative_to(self.root).as_posix() for p in self.root.rglob("*evil*")], ["ok/evil.glb"])

    def test_upload_strips_directories_and_enforces_size(self):
        saved = store.save("robot", "dir/sub/model.glb", io.BytesIO(b"glTF"))
        self.assertEqual(saved["file"], "model.glb")
        self.assertTrue((self.root / "robot" / "model.glb").is_file())
        with mock.patch.object(store, "MAX_BYTES", 3), self.assertRaises(store.AvatarError):
            store.save("robot", "big.glb", io.BytesIO(b"1234"))
        self.assertFalse((self.root / "robot" / "big.glb").exists())

    def test_active_requires_model_and_survives_tampering(self):
        store.save("pic", "face.png", io.BytesIO(b"png"))
        with self.assertRaises(store.AvatarError):
            store.set_active("pic")
        store.save("robot", "model.glb", io.BytesIO(b"glTF"))
        store.set_active("robot")
        self.assertEqual(store.active_model_url(), "/api/avatars/serve/robot/model.glb")
        (self.root / "active.txt").write_text("../../etc", encoding="utf-8")
        self.assertIsNone(store.active_model_url())

    def test_resolve_and_remove(self):
        store.save("robot", "model.glb", io.BytesIO(b"glTF"))
        self.assertEqual(store.resolve("robot", "model.glb").name, "model.glb")
        with self.assertRaises(FileNotFoundError):
            store.resolve("robot", "missing.glb")
        store.set_active("robot")
        store.remove("robot")
        self.assertEqual(store.active(), "")
        self.assertEqual(store.listing()["avatars"], [])

    def test_save_creates_missing_root_directory(self):
        nonexistent = self.root / "subfolder" / "nested_avatars"
        with mock.patch.object(store, "ROOT", nonexistent), mock.patch.object(store, "ACTIVE_FILE", nonexistent / "active.txt"):
            saved = store.save("fresh_bot", "model.glb", io.BytesIO(b"glTFbinary"))
            self.assertEqual(saved["avatar"], "fresh_bot")
            self.assertTrue((nonexistent / "fresh_bot" / "model.glb").is_file())

    def test_fbx_model_support_and_activation(self):
        saved = store.save("alien", "alien_mesh.fbx", io.BytesIO(b"Kaydara FBX Binary"))
        self.assertEqual(saved["file"], "alien_mesh.fbx")
        store.set_active("alien")
        self.assertEqual(store.active_model_url(), "/api/avatars/serve/alien/alien_mesh.fbx")

    def test_serve_avatar_mime_types(self):
        store.save("bot", "model.glb", io.BytesIO(b"glTF"))
        store.save("bot", "model.fbx", io.BytesIO(b"FBX"))
        store.save("bot", "preview.png", io.BytesIO(b"PNG"))

        glb_resp = asyncio.run(api.serve_avatar_file("bot", "model.glb"))
        self.assertEqual(glb_resp.media_type, "model/gltf-binary")

        fbx_resp = asyncio.run(api.serve_avatar_file("bot", "model.fbx"))
        self.assertEqual(fbx_resp.media_type, "application/octet-stream")

        png_resp = asyncio.run(api.serve_avatar_file("bot", "preview.png"))
        self.assertEqual(png_resp.media_type, "image/png")


if __name__ == "__main__":
    unittest.main()
