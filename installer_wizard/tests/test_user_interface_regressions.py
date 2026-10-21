import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

import node_api
from features.cameras.cameras import cameras
from features.cameras.recorder import _source_args
from features.people.photos import delete_photo
from features.people.views import kind_of
from features.nodes.registry import registry
from server.features.mesh_coordinator.p2p_mesh import p2p_mesh


class PhotoDeletionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "photos").mkdir()

    def write(self, name, data):
        path = self.folder / name
        path.write_bytes(data)
        return path

    def test_primary_and_identical_gallery_copies_are_removed(self):
        self.write("photo.jpg", b"wrong person")
        self.write("photos/photo_primary.jpg", b"wrong person")
        self.write("photos/photo_123.jpg", b"wrong person")
        self.write("photos/front_456.jpg", b"correct person")
        delete_photo(self.folder, "photo_primary", kind_of)
        self.assertEqual((self.folder / "photo.jpg").read_bytes(), b"correct person")
        self.assertFalse((self.folder / "photos/photo_primary.jpg").exists())
        self.assertFalse((self.folder / "photos/photo_123.jpg").exists())

    def test_deleting_gallery_copy_also_replaces_wrong_primary(self):
        self.write("photo.jpg", b"wrong person")
        self.write("photos/front_123.jpg", b"wrong person")
        self.write("photos/body_456.jpg", b"body image")
        delete_photo(self.folder, "front_123.jpg", kind_of)
        self.assertFalse((self.folder / "photo.jpg").exists())
        self.assertTrue((self.folder / "photos/body_456.jpg").exists())

    def test_missing_photo_does_not_change_other_files(self):
        self.write("photo.jpg", b"person")
        with self.assertRaises(FileNotFoundError):
            delete_photo(self.folder, "missing.jpg", kind_of)
        self.assertEqual((self.folder / "photo.jpg").read_bytes(), b"person")


class RtspsTest(unittest.TestCase):
    def test_rtsps_is_available_and_keeps_encrypted_url(self):
        url = "rtsps://camera.lan:7441/stream"
        camera = cameras._validate({"name": "Camera", "kind": "rtsps", "url": url}, {})
        self.assertEqual(camera["url"], url)
        self.assertEqual(_source_args(camera), ["-rtsp_transport", "tcp", "-i", url])

    def test_rtsps_kind_does_not_accept_plaintext_stream(self):
        with self.assertRaises(ValueError):
            cameras._validate({"name": "Camera", "kind": "rtsps", "url": "rtsp://camera.lan/live"}, {})


class NodeRemovalTest(unittest.TestCase):
    def test_current_host_is_protected(self):
        with self.assertRaises(HTTPException) as caught:
            node_api.delete_node(p2p_mesh.node_id)
        self.assertEqual(caught.exception.status_code, 409)

    def test_removing_paired_pc_revokes_registry_token(self):
        data = {"nodes": {"pc-studio": {"id": "pc-studio", "token": "secret"}}}
        with mock.patch.object(registry, "data", data), mock.patch.object(registry, "_save"), \
                mock.patch.object(p2p_mesh, "remove_node", return_value=False) as remove:
            result = node_api.delete_node("pc-studio")
            self.assertTrue(result["removed"])
            self.assertNotIn("pc-studio", registry.data["nodes"])
            remove.assert_called_once_with("pc-studio")

    def test_unknown_node_returns_404(self):
        with mock.patch.object(registry, "data", {"nodes": {}}), mock.patch.object(p2p_mesh, "remove_node", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                node_api.delete_node("not-found")
        self.assertEqual(caught.exception.status_code, 404)
