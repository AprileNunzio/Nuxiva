import time
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from server.features.presence_privacy.presence_service import presence_service
from server.core.sensory_bus.event_router import sensory_bus
from server.core.event_sourcing.universal_space import UniversalObservation

logger = logging.getLogger("nuxiva.vision_telemetry")

class EyeGazeState(BaseModel):
    is_looking_at_screen: bool = True
    gaze_direction: str = Field("center", description="center, left, right, up, down")
    eyes_closed: bool = False
    eye_aspect_ratio: float = Field(0.3, ge=0.0)
    blink_detected: bool = False
    drowsiness_alert: bool = False
    attention_score: float = Field(1.0, ge=0.0, le=1.0)

class HandGestureState(BaseModel):
    gesture_name: str = Field("none", description="none, swipe_left, swipe_right, fist, open_palm, thumbs_up, peace_v")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    hand_detected: bool = False
    hand_count: int = 0
    action_triggered: Optional[str] = None

class VisionTelemetryPayload(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    device_id: str = "webcam_client"
    eye_gaze: EyeGazeState = Field(default_factory=EyeGazeState)
    hand_gesture: HandGestureState = Field(default_factory=HandGestureState)
    client_fps: float = Field(30.0, ge=0.0)

class VisionTelemetryConfig(BaseModel):
    hand_gestures_enabled: bool = True
    gaze_tracking_enabled: bool = True
    auto_lock_on_looking_away_sec: float = 8.0
    drowsiness_warning_enabled: bool = True
    gesture_sensitivity: float = Field(0.75, ge=0.1, le=1.0)

class VisionTelemetryManager:
    def __init__(self) -> None:
        self.config = VisionTelemetryConfig()
        self.latest_telemetry: Optional[VisionTelemetryPayload] = None
        self._last_looking_away_start: Optional[float] = None
        self._total_gestures_processed: int = 0
        self._auto_lock_triggered: bool = False

    def update_config(self, new_config: VisionTelemetryConfig) -> VisionTelemetryConfig:
        self.config = new_config
        return self.config

    async def process_telemetry(self, payload: VisionTelemetryPayload) -> Dict[str, Any]:
        self.latest_telemetry = payload
        now = time.time()
        result_actions = []

        # 1. Elaborazione Sguardo & Attenzione (Eye Gaze)
        if self.config.gaze_tracking_enabled:
            gaze = payload.eye_gaze
            if gaze.is_looking_at_screen and not gaze.eyes_closed:
                self._last_looking_away_start = None
                self._auto_lock_triggered = False
                # Rafforza lo stato di presenza attiva biometrica
                presence_service.set_presence(
                    approaching=True,
                    verified=True,
                    user="owner"
                )
            else:
                # Sguardo distolto o occhi chiusi
                if self._last_looking_away_start is None:
                    self._last_looking_away_start = now
                elif (now - self._last_looking_away_start) >= self.config.auto_lock_on_looking_away_sec:
                    if not self._auto_lock_triggered:
                        self._auto_lock_triggered = True
                        result_actions.append("AUTO_LOCK_TRIGGERED")
                        presence_service.set_presence(
                            approaching=False,
                            verified=False,
                            user=None
                        )
                        logger.warning("Auto-lock privacy attivato: sguardo assente o prolungata distrazione.")

            if gaze.drowsiness_alert and self.config.drowsiness_warning_enabled:
                result_actions.append("DROWSINESS_WARNING")

        # 2. Elaborazione Gesti Mani (Hand Gestures)
        if self.config.hand_gestures_enabled:
            hand = payload.hand_gesture
            if hand.hand_detected and hand.gesture_name != "none" and hand.confidence >= self.config.gesture_sensitivity:
                self._total_gestures_processed += 1
                result_actions.append(f"GESTURE_{hand.gesture_name.upper()}")

                if hand.gesture_name == "fist":
                    # Pugno: blocco privacy immediato
                    presence_service.set_presence(approaching=False, verified=False, user=None)
                    result_actions.append("IMMEDIATE_PRIVACY_LOCK")
                elif hand.gesture_name in ["open_palm", "thumbs_up"]:
                    presence_service.set_presence(approaching=True, verified=True, user="owner")

        # 3. Invio al Sensory Bus per correlazione cognitiva
        try:
            obs = UniversalObservation(
                modality="vision_telemetry",
                source_id=payload.device_id,
                raw_data=payload.model_dump(),
                metadata={"timestamp": payload.timestamp, "actions": result_actions}
            )
            await sensory_bus.push_observation(obs)
        except Exception as e:
            logger.debug(f"Invio al sensory bus non bloccante: {e}")

        return {
            "status": "success",
            "actions": result_actions,
            "presence_verified": presence_service.get_status().is_biometrically_verified,
            "total_gestures": self._total_gestures_processed
        }

    def get_latest_state(self) -> Dict[str, Any]:
        return {
            "config": self.config.model_dump(),
            "latest": self.latest_telemetry.model_dump() if self.latest_telemetry else None,
            "total_gestures_processed": self._total_gestures_processed,
            "presence": presence_service.get_status().model_dump()
        }

vision_telemetry_manager = VisionTelemetryManager()
