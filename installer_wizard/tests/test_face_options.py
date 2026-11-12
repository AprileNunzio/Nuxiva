import os
import unittest
from unittest import mock

from pages import face_options
from features.avatars import store


class FaceOptionsTest(unittest.TestCase):
    def test_default_character_face_options(self):
        with mock.patch.dict(os.environ, {"NUXIVA_AVATAR_STYLE": "character"}, clear=False), \
             mock.patch.object(store, "active_model_url", return_value=None):
            opts = face_options()
            self.assertEqual(opts["style"], "character")
            self.assertEqual(opts["model"], "/vendor/Michelle.glb")
            self.assertIsNone(opts["custom_model"])
            self.assertEqual(opts["color"], "#29e0ff")

    def test_default_hologram_face_options(self):
        with mock.patch.dict(os.environ, {"NUXIVA_AVATAR_STYLE": "hologram"}, clear=False), \
             mock.patch.object(store, "active_model_url", return_value=None):
            opts = face_options()
            self.assertEqual(opts["style"], "hologram")
            self.assertEqual(opts["model"], "/static/shared/models/head.glb")
            self.assertIsNone(opts["custom_model"])

    def test_custom_avatar_propagated_to_both_styles(self):
        custom_url = "/api/avatars/serve/robot/model.glb"
        with mock.patch.dict(os.environ, {"NUXIVA_AVATAR_STYLE": "character"}, clear=False), \
             mock.patch.object(store, "active_model_url", return_value=custom_url):
            opts = face_options()
            self.assertEqual(opts["style"], "character")
            self.assertEqual(opts["model"], custom_url)
            self.assertEqual(opts["custom_model"], custom_url)

        with mock.patch.dict(os.environ, {"NUXIVA_AVATAR_STYLE": "hologram"}, clear=False), \
             mock.patch.object(store, "active_model_url", return_value=custom_url):
            opts = face_options()
            self.assertEqual(opts["style"], "hologram")
            self.assertEqual(opts["model"], custom_url)
            self.assertEqual(opts["custom_model"], custom_url)

    def test_color_and_hands_configuration(self):
        env = {
            "NUXIVA_FACE_COLOR": "#ff5500",
            "NUXIVA_AVATAR": "full",
            "NUXIVA_HANDS": "1",
            "NUXIVA_HANDS_FPS": "30",
        }
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(store, "active_model_url", return_value=None):
            opts = face_options()
            self.assertEqual(opts["color"], "#ff5500")
            self.assertEqual(opts["avatar"], "full")
            self.assertEqual(opts["hands"], "1")
            self.assertEqual(opts["hands_fps"], 30)


if __name__ == "__main__":
    unittest.main()
