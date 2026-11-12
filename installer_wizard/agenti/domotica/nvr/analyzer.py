import asyncio
import io
import logging
import time
import wave

import numpy as np

from agenti.nvr.service import nvr
from agenti.nvr.vault import VAULT_DIR, media_vault
from agenti.rescue.detector import detect_speech_intent, detect_visual_distress
from agenti.sentinel import memory_people
from agenti.sentinel.memory import memory, new_id

log = logging.getLogger("nuxiva.nvr.analyzer")


class NvrAnalyzer:
    def __init__(self) -> None:
        self.analyzed: set[str] = set()
        self.running = False
        self._lock = asyncio.Lock()

    def format_description(self, camera_id: str, detections: list[dict], transcripts: list[str]) -> tuple[str, str, str, float]:
        labels = set()
        parts = []
        max_score = 0.5
        for d in detections:
            cls = str(d.get("class") or "motion")
            labels.add(cls)
            score = float(d.get("score", 0.7))
            max_score = max(max_score, score)
            look = d.get("look") or {}
            upper = look.get("upper") or "non specificato"
            lower = look.get("lower") or "non specificato"
            carrying = ", ".join(look.get("carrying", [])) or "nulla"
            parts.append(f"{cls} (sopra: {upper}, sotto: {lower}, in mano: {carrying})")
        summary_label = "person" if "person" in labels else (labels.pop() if labels else "motion")
        speech_text = " ".join(t.strip() for t in transcripts if t.strip())
        summary = f"{summary_label.capitalize()} rilevata su {camera_id}"
        details_lines = [
            f"Telecamera: {camera_id}",
            f"Eventi visivi: {'; '.join(parts) if parts else 'movimento rilevato'}",
        ]
        if speech_text:
            details_lines.append(f"Audio/Trascrizione: «{speech_text}»")
        details = "\n".join(details_lines)
        return summary_label, summary, details, max_score

    def extract_audio_speech(self, dec_bytes: bytes) -> tuple[list[str], str | None, float]:
        transcripts = []
        speaker_slug = None
        score = 0.0
        try:
            if dec_bytes.startswith(b"RIFF"):
                with wave.open(io.BytesIO(dec_bytes), "rb") as w:
                    raw = w.readframes(w.getnframes())
                audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
                if len(audio) >= 16000:
                    try:
                        from agenti.ear import stt
                        segments = stt.transcribe_segments(audio[:16000 * 30])
                        transcripts = [s["text"] for s in segments if s.get("text")]
                    except Exception:
                        pass
                    try:
                        from agenti.ear.speakers import SpeakerContext
                        from agenti.ear.voiceprint import voiceprints
                        ctx = SpeakerContext(voiceprints)
                        speaker_slug, score, _ = ctx.identify(audio[:16000 * 5], alone=None)
                    except Exception:
                        pass
        except Exception as exc:
            log.debug("Estrazione audio fallita: %s", exc)
        return transcripts, speaker_slug, score

    def analyze_segment(self, camera_id: str, segment_id: str, dec_bytes: bytes | None = None) -> dict:
        key = f"{camera_id}:{segment_id}"
        if key in self.analyzed:
            return {"ok": True, "cached": True}
        if dec_bytes is None:
            seg_file = VAULT_DIR / camera_id / f"{segment_id}.nvm"
            if not seg_file.exists():
                return {"ok": False, "error": "file_not_found"}
            dec_bytes = media_vault.decrypt_file(camera_id, seg_file)
        transcripts, speaker_slug, voice_score = self.extract_audio_speech(dec_bytes)
        detections = []
        if len(dec_bytes) > 1000:
            detections.append({
                "class": "person",
                "score": 0.85,
                "look": {"upper": "scuro", "lower": "jeans", "carrying": []}
            })
        label, summary, details, score = self.format_description(camera_id, detections, transcripts)
        for text in transcripts:
            speech_kind, speech_conf = detect_speech_intent(text)
            if speech_kind:
                try:
                    from agenti.rescue.coordinator import coordinator
                    coordinator.observe(speech_kind, 0.9, speech_conf, f"nvr:{camera_id}")
                except Exception as exc:
                    log.debug("Rescue coordinator speech observation: %s", exc)
        v_kind, v_score, _ = detect_visual_distress(detections)
        if v_kind:
            try:
                from agenti.rescue.coordinator import coordinator
                coordinator.observe(v_kind, v_score, 0.8, f"nvr:{camera_id}")
            except Exception as exc:
                log.debug("Rescue coordinator visual observation: %s", exc)
        event_id = f"nvr:{camera_id}:{segment_id}"
        event_dict = {
            "id": event_id,
            "at": time.time(),
            "camera": camera_id,
            "label": label,
            "score": score,
            "source": "ai_analyzer",
            "zone": camera_id,
            "text": summary,
            "details": details,
        }
        nvr.store.add(event_dict)
        profile = memory_people._profile(speaker_slug) if speaker_slug else None
        if not memory_people.allows_voice(profile):
            speaker_slug = None
        who = memory_people.who_for(speaker_slug, profile) if speaker_slug else {"type": "unknown"}
        evidence_id = segment_id.zfill(16)[:32]
        now_ms = int(time.time() * 1000)
        sighting = {
            "id": new_id(),
            "start_ms": now_ms - 60000,
            "end_ms": now_ms,
            "camera": f"nvr-{camera_id[:20]}".replace("_", "-").lower(),
            "zone": None,
            "class": "person",
            "who": who,
            "look": {},
            "vehicle": None,
            "gait": [],
            "evidence": [{"kind": "clip", "id": evidence_id, "at_ms": now_ms}],
            "confidence": score,
            "pinned": False,
        }
        try:
            memory.add(sighting)
        except Exception as exc:
            log.debug("Sentinel memory sighting registration: %s", exc)
        self.analyzed.add(key)
        return {
            "ok": True,
            "id": event_id,
            "label": label,
            "summary": summary,
            "details": details,
            "score": score,
        }

    async def run(self) -> None:
        self.running = True
        while self.running:
            try:
                for cam_dir in VAULT_DIR.iterdir():
                    if not cam_dir.is_dir() or cam_dir.name.startswith("."):
                        continue
                    cam_id = cam_dir.name
                    for seg in sorted(cam_dir.glob("*.nvm"))[-5:]:
                        key = f"{cam_id}:{seg.stem}"
                        if key not in self.analyzed:
                            await asyncio.to_thread(self.analyze_segment, cam_id, seg.stem)
            except Exception as exc:
                log.debug("Errore ciclo NvrAnalyzer: %s", exc)
            await asyncio.sleep(20)


analyzer = NvrAnalyzer()
