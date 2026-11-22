import asyncio
import base64
import unittest
import numpy as np

from server.features.human_affective_engine.interfaces import (
    MoodState,
    VocalDeliveryMode,
    VoiceAudioAnalysisPayload,
)
from server.features.human_affective_engine.vocal_biomarker_extractor import VocalBiomarkerAnalyzer
from server.features.human_affective_engine.affective_fusion_engine import affective_fusion_engine
from server.features.human_affective_engine.adaptive_response_orchestrator import adaptive_response_orchestrator
from server.features.human_affective_engine.affective_service import human_affective_service
from server.features.chatbot_mesh.chatbot_models import ChatMessagePayload, UserAgentPersonalization
from server.features.chatbot_mesh.conversational_engine import conversational_bot_engine
from server.features.chatbot_mesh.user_agent_customization_service import user_agent_customization_service


def _synthesize_whisper(sample_rate: int = 16000, duration_s: float = 1.5) -> np.ndarray:
    """Genera un segnale sintetico di sussurro: turbolenza aperiodica ad alta frequenza e bassa energia."""
    rng = np.random.default_rng(42)
    n = int(sample_rate * duration_s)
    noise = rng.standard_normal(n).astype(np.float32)
    # High-pass filter via FFT (1800 Hz - 5500 Hz) to emulate unvoiced whisper airflow
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    band = (freqs >= 1800.0) & (freqs <= 5500.0)
    spec[~band] = 0.0
    whisper = np.fft.irfft(spec, n=n).astype(np.float32)
    # Gentle syllable-like amplitude modulation (~3 Hz)
    t = np.linspace(0.0, duration_s, n, dtype=np.float32)
    envelope = 0.55 + 0.45 * np.sin(2.0 * np.pi * 3.0 * t)
    whisper = whisper * envelope
    # Normalize to soft whisper RMS (~0.03)
    rms = float(np.sqrt(np.mean(whisper ** 2))) + 1e-9
    return (whisper / rms) * 0.03


def _synthesize_normal_voiced(sample_rate: int = 16000, duration_s: float = 1.5, f0: float = 160.0) -> np.ndarray:
    """Genera un segnale vocale sonoro con armoniche nette e volume conversazionale normale."""
    n = int(sample_rate * duration_s)
    t = np.linspace(0.0, duration_s, n, dtype=np.float32)
    voiced = (
        0.65 * np.sin(2.0 * np.pi * f0 * t)
        + 0.25 * np.sin(2.0 * np.pi * 2.0 * f0 * t)
        + 0.10 * np.sin(2.0 * np.pi * 3.0 * f0 * t)
    ).astype(np.float32)
    envelope = 0.65 + 0.35 * np.sin(2.0 * np.pi * 3.2 * t)
    voiced = voiced * envelope
    rms = float(np.sqrt(np.mean(voiced ** 2))) + 1e-9
    return (voiced / rms) * 0.18


def _to_pcm16_b64(signal: np.ndarray) -> str:
    clipped = np.clip(signal, -1.0, 1.0)
    pcm16 = (clipped * 32767.0).astype("<i2").tobytes()
    return base64.b64encode(pcm16).decode("ascii")


class TestParalinguisticAdaptiveResponse(unittest.TestCase):
    def setUp(self):
        self.analyzer = VocalBiomarkerAnalyzer(sample_rate=16000)

    def tearDown(self):
        for uid in [
            "user_whisper_11labs",
            "user_whisper_azure",
            "user_whisper_piper",
            "user_whisper_chat_e2e",
            "user_voice_service",
        ]:
            adaptive_response_orchestrator.clear_user_affect(uid)

    def test_whisper_acoustic_detection_vs_voiced_and_silence(self):
        whisper_bio = self.analyzer.extract_biomarkers(_synthesize_whisper())
        voiced_bio = self.analyzer.extract_biomarkers(_synthesize_normal_voiced())
        silence_bio = self.analyzer.extract_biomarkers(np.zeros(16000, dtype=np.float32))

        self.assertGreaterEqual(whisper_bio.whisper_probability, 0.65)
        self.assertEqual(whisper_bio.delivery_mode, VocalDeliveryMode.WHISPER)
        self.assertGreater(whisper_bio.high_freq_energy_ratio, 0.70)
        self.assertLess(whisper_bio.harmonic_to_noise_ratio_db, 2.0)

        self.assertLess(voiced_bio.whisper_probability, 0.25)
        self.assertNotEqual(voiced_bio.delivery_mode, VocalDeliveryMode.WHISPER)
        self.assertGreater(voiced_bio.voicing_strength, 0.60)
        self.assertGreater(voiced_bio.harmonic_to_noise_ratio_db, 4.0)

        self.assertEqual(silence_bio.whisper_probability, 0.0)

    def test_voice_only_whisper_inference_and_tts_modulation(self):
        whisper_bio = self.analyzer.extract_biomarkers(_synthesize_whisper())
        result = affective_fusion_engine.infer_from_voice_only("user_whisper_11labs", whisper_bio)

        self.assertEqual(result.vocal_delivery_mode, VocalDeliveryMode.WHISPER)
        self.assertGreaterEqual(result.whisper_probability, 0.65)
        self.assertNotEqual(result.detected_mood, MoodState.DEPRESSED_DYSPHORIC)
        self.assertTrue(result.voice_tone_guidance["whisper_mode"])
        self.assertLessEqual(result.voice_tone_guidance["volume_db"], -8.0)
        self.assertLessEqual(result.voice_tone_guidance["speed"], 0.86)
        self.assertEqual(result.voice_tone_guidance["tts_style_hint"], "whispering")

    def test_engine_aware_whisper_prompt_modulation(self):
        whisper_bio = self.analyzer.extract_biomarkers(_synthesize_whisper())
        base_prompt = "Sei Nuxiva, assistente vocale empatico."

        for uid, engine, expected_snippet in [
            ("user_whisper_11labs", "elevenlabs", "[whispering]"),
            ("user_whisper_azure", "azure", "<style:whispering>"),
            ("user_whisper_piper", "piper", "NON inserire MAI tag tra parentesi quadre"),
        ]:
            inference = affective_fusion_engine.infer_from_voice_only(uid, whisper_bio)
            adaptive_response_orchestrator.register_inference(inference)
            modulated = adaptive_response_orchestrator.modulate_system_prompt(
                uid, base_prompt, tts_engine=engine
            )
            self.assertIn("Modalità vocale rilevata: WHISPER", modulated)
            self.assertIn(expected_snippet, modulated)
            self.assertIn("NON usare frasi preconfezionate", modulated)

    def test_affective_service_voice_payload_processing(self):
        payload = VoiceAudioAnalysisPayload(
            user_id="user_voice_service",
            sample_rate=16000,
            pcm16_b64=_to_pcm16_b64(_synthesize_whisper()),
        )
        result = asyncio.run(human_affective_service.process_voice_payload(payload))
        self.assertEqual(result.vocal_delivery_mode, VocalDeliveryMode.WHISPER)
        latest = human_affective_service.get_latest_user_affect("user_voice_service")
        self.assertIsNotNone(latest)
        self.assertTrue(latest.voice_tone_guidance["whisper_mode"])

    def test_conversational_engine_end_to_end_whisper_adaptation(self):
        user_id = "user_whisper_chat_e2e"
        agent_id = "chief_supervisor"
        user_agent_customization_service.save_personalization(
            UserAgentPersonalization(
                user_id=user_id,
                agent_id=agent_id,
                tts_engine="elevenlabs",
            )
        )

        payload = ChatMessagePayload(
            user_id=user_id,
            agent_id=agent_id,
            text="Ehi, sei sveglia? Non riesco a dormire...",
            audio_pcm16_b64=_to_pcm16_b64(_synthesize_whisper()),
            audio_sample_rate=16000,
        )
        response = asyncio.run(conversational_bot_engine.handle_message(payload))

        self.assertTrue(response.voice_modulation.get("whisper_mode"))
        self.assertLessEqual(response.voice_modulation.get("volume_db", 0.0), -8.0)

        modulated_prompt = conversational_bot_engine.build_personalized_system_prompt(user_id, agent_id)
        self.assertIn("WHISPER", modulated_prompt)
        self.assertIn("[whispering]", modulated_prompt)
        self.assertIn("NON usare frasi preconfezionate", modulated_prompt)

    def test_tts_audio_modulation_and_user_resolution(self):
        from server.features.voice_biometrics.audio_contracts import TTSRequest
        from server.features.voice_biometrics.tts_engine import apply_vocal_modulation, tts_engine

        # 1. Verifica che resolve_modulation erediti lo stato sussurro dell'utente
        user_id = "user_whisper_11labs"
        whisper_bio = self.analyzer.extract_biomarkers(_synthesize_whisper())
        inference = affective_fusion_engine.infer_from_voice_only(user_id, whisper_bio)
        adaptive_response_orchestrator.register_inference(inference)

        req = TTSRequest(text="Va bene, resto qui con te.", user_id=user_id)
        speed, volume_db, whisper_mode = tts_engine.resolve_modulation(req)
        self.assertTrue(whisper_mode)
        self.assertLessEqual(volume_db, -8.0)
        self.assertLessEqual(speed, 0.86)

        # 2. Verifica che apply_vocal_modulation abbassi realmente l'energia RMS in uscita
        voiced = _synthesize_normal_voiced(sample_rate=22050, duration_s=0.5, f0=180.0)
        raw_pcm = (np.clip(voiced, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        modulated_pcm = apply_vocal_modulation(raw_pcm, sample_rate=22050, volume_db=-8.0, whisper_mode=True)

        orig_rms = float(np.sqrt(np.mean((np.frombuffer(raw_pcm, dtype="<i2").astype(np.float32) / 32768.0) ** 2)))
        mod_rms = float(np.sqrt(np.mean((np.frombuffer(modulated_pcm, dtype="<i2").astype(np.float32) / 32768.0) ** 2)))
        self.assertLess(mod_rms, orig_rms * 0.45)


if __name__ == "__main__":
    unittest.main()
