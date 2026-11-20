import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agenti.agency.media_production import (
    AudioProducerEngine,
    MultimediaOrchestrator,
    SMBAudioHarvester,
    VideoEditorSyncDirector,
)
from agenti.agency.scanner.department_scanner import scan_departments
from agenti.agency.tools import Context
from agenti.agency.tools_catalog.media_tools import TOOLS as MEDIA_TOOLS


class TestAgencyMultimediaProduction(unittest.TestCase):
    def test_smb_audio_scanning_and_harvesting(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            music_dir = base / "soundtracks" / "epic"
            music_dir.mkdir(parents=True, exist_ok=True)

            f1 = music_dir / "intro_beat.mp3"
            f1.write_bytes(b"ID3" + b"\x00" * 32000)

            f2 = music_dir / "outro_jingle.wav"
            f2.write_bytes(b"RIFF" + b"\x00" * 48000)

            doc_dir = base / "docs"
            doc_dir.mkdir(parents=True, exist_ok=True)
            (doc_dir / "readme.txt").write_text("not an audio file", encoding="utf-8")

            scanned = SMBAudioHarvester.scan_smb_audio_shares(base, recursive=True)
            self.assertEqual(len(scanned), 2)
            names = {f["name"] for f in scanned}
            self.assertIn("intro_beat.mp3", names)
            self.assertIn("outro_jingle.wav", names)

            harvested = SMBAudioHarvester.fetch_smb_audio(f1, target_dir=base / "cache")
            self.assertEqual(harvested["status"], "harvested")
            self.assertEqual(harvested["filename"], "intro_beat.mp3")
            self.assertTrue(Path(harvested["cached_path"]).exists())

    def test_audio_producer_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            text = "Benvenuti nel canale ufficiale. Oggi scopriamo le novità."
            res = AudioProducerEngine.generate_synthetic_audio(
                text=text,
                voice_profile="it-IT-ElsaNeural",
                style="vibrant",
                pacing_bpm=140,
                output_dir=tmp_dir,
            )
            self.assertEqual(res["status"], "synthesized")
            self.assertEqual(res["word_count"], 8)
            self.assertGreater(res["duration_sec"], 2.0)
            self.assertEqual(len(res["word_timings"]), 8)
            self.assertTrue(Path(res["file_path"]).exists())

    def test_video_editor_sync_timeline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_track = {
                "file_path": "/tmp/test_audio.wav",
                "duration_sec": 12.0,
                "word_timings": [
                    {"word": "Nuovo", "start": 0.0, "end": 0.5, "duration": 0.5},
                    {"word": "Lancio", "start": 0.5, "end": 1.0, "duration": 0.5},
                    {"word": "Prodotto", "start": 1.0, "end": 1.8, "duration": 0.8},
                ]
            }
            scenes = [
                {"title": "Gancio Iniziale", "visual_prompt": "Futuristic skyline with neon lights", "transition": "wipe"},
                {"title": "Dimostrazione Core", "visual_prompt": "Screen preview of autonomous agent", "transition": "fade"},
            ]
            synced = VideoEditorSyncDirector.sync_audio_video_timeline(
                video_scenes=scenes,
                audio_track=audio_track,
                target_aspect="9:16",
                output_dir=tmp_dir,
            )
            self.assertEqual(synced["status"], "timeline_synchronized")
            self.assertEqual(synced["target_aspect"], "9:16")
            self.assertEqual(synced["resolution"], "1080x1920")
            self.assertEqual(len(synced["scene_cuts"]), 2)
            self.assertTrue(Path(synced["srt_path"]).exists())
            srt_content = Path(synced["srt_path"]).read_text(encoding="utf-8")
            self.assertIn("Nuovo Lancio Prodotto", srt_content)
            self.assertIn("ffmpeg", synced["ffmpeg_pipeline"])

    def test_multimedia_orchestrator_omnichannel_reel(self):
        res = MultimediaOrchestrator.orchestrate_omnichannel_reel(
            title="Lancio AI Automation",
            topic="Intelligenza Artificiale Autonoma",
            platform="tiktok",
            aspect_ratio="9:16",
            voice_text="Ecco la rivoluzione dell'automazione autonoma per la tua azienda.",
        )
        self.assertEqual(res["status"], "multimedia_reel_ready")
        self.assertEqual(res["platform"], "tiktok")
        self.assertEqual(res["pair_assignment"]["left_desk"], "video_editor")
        self.assertIn("video_timeline", res)
        self.assertEqual(res["video_timeline"]["resolution"], "1080x1920")

    def test_departments_creative_video_editor_and_audio_producer(self):
        deps = scan_departments()
        self.assertIn("video_editor", deps)
        self.assertIn("audio_producer", deps)

        v_dep = deps["video_editor"]
        self.assertEqual(v_dep["name"], "Leo · Video Editor & Sound Sync Director")
        self.assertIn("creative", v_dep["category"])
        self.assertIn("audio-sync", v_dep["skills"])

        a_dep = deps["audio_producer"]
        self.assertEqual(a_dep["name"], "Marco · Sound Designer & Audio Producer")
        self.assertIn("creative", a_dep["category"])
        self.assertIn("neural-voice-generation", a_dep["skills"])

    def test_media_tools_execution(self):
        ctx = Context(project_id="proj_media_test", folder="/tmp/test_media_folder")

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            sample_audio = base / "track.mp3"
            sample_audio.write_bytes(b"ID3" + b"\x00" * 16000)

            harvest_out = asyncio.run(MEDIA_TOOLS["smb_audio_harvest"].run(ctx, {
                "smb_path": str(base),
                "recursive": True,
            }))
            harvest_data = json.loads(harvest_out)
            self.assertEqual(harvest_data["status"], "smb_scanned")
            self.assertEqual(harvest_data["count"], 1)

            synth_out = asyncio.run(MEDIA_TOOLS["audio_producer_synthesize"].run(ctx, {
                "text": "Sintesi vocale autonoma completata.",
                "voice_profile": "it-IT-DiegoNeural",
                "pacing_bpm": 120,
            }))
            synth_data = json.loads(synth_out)
            self.assertEqual(synth_data["status"], "synthesized")
            self.assertIn("file_path", synth_data)

            reel_out = asyncio.run(MEDIA_TOOLS["omnichannel_reel_produce"].run(ctx, {
                "title": "Drop Prodotto",
                "topic": "Nuove Funzionalità",
                "platform": "instagram_reels",
                "voice_text": "Non perderti le nuove funzionalità in arrivo.",
            }))
            reel_data = json.loads(reel_out)
            self.assertEqual(reel_data["status"], "multimedia_reel_ready")

    def test_specialist_routing_video_and_audio(self):
        from agenti.agency.scanner.department_scanner import find_specialist
        v_spec = find_specialist("voglio montare un video con sincronizzazione tagli audio")
        self.assertIsNotNone(v_spec)
        self.assertEqual(v_spec["id"], "video_editor")

        a_spec = find_specialist("prendo traccia audio musicale e jingle da cartella smb")
        self.assertIsNotNone(a_spec)
        self.assertEqual(a_spec["id"], "audio_producer")

