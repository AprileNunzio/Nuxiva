import time
from dataclasses import asdict, dataclass, field

PHASE_IDLE = "idle"
PHASE_LISTENING = "listening"
PHASE_THINKING = "thinking"
PHASE_SPEAKING = "speaking"
PHASE_BARGED_IN = "barged_in"


@dataclass
class VoiceStreamSession:
    session_id: str
    active_speaker_slug: str | None = None
    phase: str = PHASE_IDLE
    current_utterance: str = ""
    playback_position_ms: int = 0
    barge_in_count: int = 0
    pacing_bpm: int = 70
    latency_ms: float = 45.0
    history: list[dict] = field(default_factory=list)

    def on_user_speech_start(self, now_ms: int | None = None) -> dict:
        was_speaking = self.phase == PHASE_SPEAKING
        if was_speaking:
            self.phase = PHASE_BARGED_IN
            self.barge_in_count += 1
            action = "immediate_mute_suppression"
        else:
            self.phase = PHASE_LISTENING
            action = "listen_stream_opened"

        record = {
            "timestamp": now_ms or int(time.time() * 1000),
            "event": "user_speech_detected",
            "action": action,
            "was_interrupted": was_speaking,
            "suppression_latency_ms": 28.5 if was_speaking else 0.0,
        }
        self.history.append(record)
        return record

    def on_llm_chunk(self, chunk_text: str) -> dict:
        if self.phase == PHASE_BARGED_IN:
            return {"status": "dropped_due_to_barge_in", "chunk": chunk_text}
        self.phase = PHASE_SPEAKING
        self.current_utterance += chunk_text
        return {
            "status": "stream_pushed",
            "chunk": chunk_text,
            "pacing_bpm": self.pacing_bpm,
            "render_mode": "borderless_holographic_audio",
        }

    def finish_speech(self) -> None:
        if self.phase != PHASE_BARGED_IN:
            self.phase = PHASE_IDLE
        self.current_utterance = ""

    def adjust_pacing(self, context_kind: str) -> int:
        if context_kind == "bedtime_story":
            self.pacing_bpm = 52
        elif context_kind in ("emergency", "firewall_alert"):
            self.pacing_bpm = 95
        else:
            self.pacing_bpm = 70
        return self.pacing_bpm


class VoiceBridgeGovernor:
    def __init__(self) -> None:
        self.sessions: dict[str, VoiceStreamSession] = {}

    def get_or_create(self, session_id: str = "master_duplex") -> VoiceStreamSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = VoiceStreamSession(session_id=session_id)
        return self.sessions[session_id]

    def trigger_barge_in(self, session_id: str = "master_duplex") -> dict:
        sess = self.get_or_create(session_id)
        return sess.on_user_speech_start()

    def snapshot(self, session_id: str = "master_duplex") -> dict:
        sess = self.get_or_create(session_id)
        return asdict(sess)


voice_governor = VoiceBridgeGovernor()
