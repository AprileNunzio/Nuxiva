import json
import time
from pathlib import Path
from config import DEMO, STATE_DIR, read_env

SESSION_FILE = STATE_DIR / "setup_session.json"

DEFAULT_CONFIG = {
    "locale": "it-IT",
    "timezone": "Europe/Rome",
    "assistant_name": "Aria",
    "assistant_gender": "female",
    "wake_word_primary": "aria",
    "wake_phrases": ["aria", "ehi aria", "ok aria", "ciao aria"],
    "wake_phonetic_aliases": ["aria", "arya", "harya"],
    "voice_id": "if_sara",
    "mic_device_id": "hw:0,0",
    "mic_noise_floor_db": -58.2,
    "mic_snr_db": 27.4,
    "mic_gain_db": 4.5,
    "mic_vad_threshold": 0.28,
    "brain_preset": "nuxiva-6.5-auto",
    "owner_name": "",
    "owner_last": "",
    "face_enrolled": False,
    "cameras": [],
    "ha_url": "",
    "ha_token": "",
    "cloud_provider": "gemini",
    "cloud_key": "",
    "brain_mode": "local"
}

class SetupSession:
    def __init__(self) -> None:
        self.current_step = 1
        self.max_reached_step = 1
        self.steps_meta = {
            str(i): {
                "status": "active" if i == 1 else "pending",
                "dirty": False,
                "score": 100 if i == 1 else 0
            }
            for i in range(1, 8)
        }
        self.config = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        if not SESSION_FILE.exists():
            env = read_env()
            if env.get("NUXIVA_ASSISTANT_NAME"):
                name = env["NUXIVA_ASSISTANT_NAME"].strip()
                self.config["assistant_name"] = name
                clean = name.lower().replace("hey ", "").replace("ehi ", "").strip()
                self.config["wake_word_primary"] = clean
                self.config["wake_phrases"] = [clean, f"ehi {clean}", f"ok {clean}", f"ciao {clean}"]
                self.config["wake_phonetic_aliases"] = [clean]
            if env.get("NUXIVA_UI_LANG"):
                self.config["locale"] = f"{env['NUXIVA_UI_LANG']}-{env['NUXIVA_UI_LANG'].upper()}"
            if env.get("NUXIVA_VOICE"):
                self.config["voice_id"] = env["NUXIVA_VOICE"]
            return
        try:
            raw = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            self.current_step = int(raw.get("current_step", 1))
            self.max_reached_step = int(raw.get("max_reached_step", 1))
            self.steps_meta = raw.get("steps_meta", self.steps_meta)
            self.config.update(raw.get("config", {}))
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = SESSION_FILE.with_suffix(".tmp")
            data = self.to_dict()
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(SESSION_FILE)
        except OSError:
            pass

    def to_dict(self) -> dict:
        return {
            "current_step": self.current_step,
            "max_reached_step": self.max_reached_step,
            "steps_meta": self.steps_meta,
            "config": self.config
        }

    def navigate(self, target_step: int) -> dict:
        if target_step < 1 or target_step > 7:
            raise ValueError("Target step out of bounds")
        if target_step > self.max_reached_step + 1:
            raise ValueError("Target step locked")
        prev_step = self.current_step
        self.current_step = target_step
        if target_step > self.max_reached_step:
            self.max_reached_step = target_step
        for k in self.steps_meta:
            ik = int(k)
            if ik < target_step:
                if self.steps_meta[k]["status"] != "completed":
                    self.steps_meta[k]["status"] = "completed"
            elif ik == target_step:
                self.steps_meta[k]["status"] = "active"
            else:
                if self.steps_meta[k]["status"] != "completed":
                    self.steps_meta[k]["status"] = "pending"
        self.save()
        return self.to_dict()

    def update_config(self, step: int, updates: dict) -> dict:
        self.config.update(updates)
        self._apply_invalidation(step, updates)
        score = int(updates.get("score", 100))
        self.steps_meta[str(step)]["score"] = score
        self.steps_meta[str(step)]["dirty"] = False
        self.steps_meta[str(step)]["status"] = "completed"
        if step == self.max_reached_step and step < 7:
            self.max_reached_step = step + 1
            self.steps_meta[str(step + 1)]["status"] = "active"
        self.save()
        return self.to_dict()

    def _apply_invalidation(self, step: int, updates: dict) -> None:
        if step == 1 and "locale" in updates:
            self.steps_meta["3"]["dirty"] = True
        elif step == 2 and "mic_device_id" in updates:
            self.steps_meta["3"]["dirty"] = True
            self.steps_meta["4"]["dirty"] = True

    def release_hardware(self) -> dict:
        return {"ok": True, "released": ["audio_stream", "camera_stream"]}

session_manager = SetupSession()
