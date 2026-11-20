import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.voices import audio_vault, catalog, elevenlabs_client
from agenti.voices.api import admin_routes


class ElevenLabsAndVaultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_vault_dir = audio_vault.VAULT_DIR
        self.original_index_file = audio_vault.INDEX_FILE

        audio_vault.VAULT_DIR = Path(self.tmp.name) / "vault"
        audio_vault.INDEX_FILE = audio_vault.VAULT_DIR / "vault_index.json"
        audio_vault._ensure_vault()

        self.vault = audio_vault.AudioVault()

        app = FastAPI()
        app.dependency_overrides[require_admin] = lambda: "admin"
        app.include_router(admin_routes)
        self.client = TestClient(app)

    def tearDown(self):
        audio_vault.VAULT_DIR = self.original_vault_dir
        audio_vault.INDEX_FILE = self.original_index_file
        self.tmp.cleanup()

    def test_catalog_elevenlabs_recognition(self):
        voice_id = "eleven_21m00Tcm4TlvDq8ikWAM"
        self.assertTrue(catalog.is_elevenlabs(voice_id))
        self.assertFalse(catalog.is_elevenlabs("if_sara"))
        self.assertEqual(catalog.engine(voice_id), "elevenlabs")
        desc = catalog.describe(voice_id)
        self.assertEqual(desc["engine"], "elevenlabs")
        self.assertIn("21m00tcm4tlvdq8ikwam", desc["name"].lower())

    def test_elevenlabs_unconfigured_subscription(self):
        with mock.patch.dict("os.environ", {"NUXIVA_ELEVENLABS_API_KEY": ""}):
            info = elevenlabs_client.get_subscription_info()
            self.assertFalse(info["configured"])
            self.assertEqual(info["tier"], "none")
            self.assertEqual(info["status"], "unconfigured")

    def test_elevenlabs_subscription_parsing(self):
        mock_resp = json.dumps({
            "tier": "free",
            "character_count": 2500,
            "character_limit": 10000,
            "status": "active",
            "can_extend_character_limit": False,
            "allowed_to_use_instant_voice_cloning": False,
            "next_invoice": {"next_payment_attempt": 1800000000},
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            cm = mock.MagicMock()
            cm.read.return_value = mock_resp
            mock_urlopen.return_value.__enter__.return_value = cm

            info = elevenlabs_client.get_subscription_info(api_key="sk_test_123")
            self.assertTrue(info["configured"])
            self.assertEqual(info["tier"], "free")
            self.assertEqual(info["character_count"], 2500)
            self.assertEqual(info["remaining_characters"], 7500)
            self.assertEqual(info["percent_used"], 25.0)

    def test_audio_vault_store_and_lookup(self):
        dummy_wav = b"RIFF" + b"\x00" * 200
        text = "Luce del salotto accesa"
        clip_id = self.vault.store(text, "eleven_rachel", "elevenlabs", dummy_wav, pinned=False)
        self.assertTrue(bool(clip_id))

        # First hit
        hit = self.vault.lookup(text, "eleven_rachel", "elevenlabs")
        self.assertIsNotNone(hit)
        self.assertEqual(hit, dummy_wav)

        stats = self.vault.get_stats()
        self.assertEqual(stats["total_clips"], 1)
        self.assertEqual(stats["total_hits"], 1)
        self.assertEqual(stats["total_chars_saved"], len(text))

        clips = self.vault.list_clips()
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["hit_count"], 1)
        self.assertEqual(clips[0]["chars_saved"], len(text))

    def test_audio_vault_clear_unpinned(self):
        dummy_wav = b"RIFF" + b"\x00" * 150
        self.vault.store("Frase temporanea", "if_sara", "kokoro", dummy_wav, pinned=False)
        self.vault.store("Frase permanente", "if_sara", "kokoro", dummy_wav, pinned=True)

        self.assertEqual(self.vault.get_stats()["total_clips"], 2)
        deleted = self.vault.clear_unpinned()
        self.assertEqual(deleted, 1)
        self.assertEqual(self.vault.get_stats()["total_clips"], 1)

    def test_engine_routes(self):
        res = self.client.get("/api/voices/engine")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("engine_mode", data)
        self.assertIn("speed", data)

        res_put = self.client.put("/api/voices/engine", json={"engine_mode": "hybrid", "speed": 1.15})
        self.assertEqual(res_put.status_code, 200)
        updated = res_put.json()
        self.assertEqual(updated["engine_mode"], "hybrid")
        self.assertEqual(updated["speed"], 1.15)

    def test_vault_api_routes(self):
        res_stats = self.client.get("/api/voices/vault/stats")
        self.assertEqual(res_stats.status_code, 200)
        self.assertIn("total_chars_saved", res_stats.json())

        res_clips = self.client.get("/api/voices/vault/clips")
        self.assertEqual(res_clips.status_code, 200)
        self.assertIn("clips", res_clips.json())


if __name__ == "__main__":
    unittest.main()
