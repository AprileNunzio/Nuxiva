import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActuationCommand:
    domain: str
    target_id: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    room_id: str = "default_room"
    executed_at: float = field(default_factory=time.time)


class UnifiedPhysicalActuationBridge:
    def __init__(self) -> None:
        self.command_log: list[ActuationCommand] = []
        self.active_room_states: dict[str, dict[str, Any]] = {}

    def execute_command(self, cmd: ActuationCommand) -> dict[str, Any]:
        self.command_log.append(cmd)
        room_state = self.active_room_states.setdefault(cmd.room_id, {
            "room_id": cmd.room_id,
            "lights": {"power": "on", "brightness": 80, "color_temp_k": 4000},
            "climate": {"target_temp_c": 21.0, "mode": "auto"},
            "audio": {"playing": False, "track": None, "volume": 30},
        })

        if cmd.domain == "light":
            lights = room_state.setdefault("lights", {})
            lights["power"] = "on" if cmd.action in ("turn_on", "set_scene") else "off"
            if "brightness" in cmd.parameters:
                lights["brightness"] = int(cmd.parameters["brightness"])
            if "color_temp_k" in cmd.parameters:
                lights["color_temp_k"] = int(cmd.parameters["color_temp_k"])

        elif cmd.domain == "climate":
            climate = room_state.setdefault("climate", {})
            if "temperature" in cmd.parameters:
                climate["target_temp_c"] = float(cmd.parameters["temperature"])
            if "mode" in cmd.parameters:
                climate["mode"] = str(cmd.parameters["mode"])

        elif cmd.domain == "audio":
            audio = room_state.setdefault("audio", {})
            audio["playing"] = cmd.action == "play"
            if "track" in cmd.parameters:
                audio["track"] = str(cmd.parameters["track"])
            if "volume" in cmd.parameters:
                audio["volume"] = int(cmd.parameters["volume"])

        return {
            "status": "executed",
            "domain": cmd.domain,
            "target_id": cmd.target_id,
            "action": cmd.action,
            "room_id": cmd.room_id,
            "resulting_state": room_state,
        }

    def apply_preset_scene(self, scene_name: str, room_id: str) -> dict[str, Any]:
        scenes = {
            "focus_work_office": {
                "lights": {"brightness": 95, "color_temp_k": 5500},
                "audio": {"action": "play", "track": "binaural_focus_alpha", "volume": 20},
            },
            "socratic_study_mode": {
                "lights": {"brightness": 85, "color_temp_k": 4200},
                "audio": {"action": "play", "track": "classical_didactic_piano", "volume": 25},
            },
            "chef_cooking_preset": {
                "lights": {"brightness": 100, "color_temp_k": 5000},
                "audio": {"action": "play", "track": "kitchen_acoustic_rhythm", "volume": 35},
            },
            "bedtime_calm_dreamscape": {
                "lights": {"brightness": 12, "color_temp_k": 2000},
                "audio": {"action": "play", "track": "delta_waves_sleep_frequencies", "volume": 15},
            },
            "co_presence_privacy_lockdown": {
                "lights": {"brightness": 50, "color_temp_k": 3000},
                "audio": {"action": "stop", "track": None, "volume": 0},
            },
        }

        config = scenes.get(scene_name, scenes["focus_work_office"])
        light_cmd = ActuationCommand(
            domain="light",
            target_id=f"lights_{room_id}",
            action="set_scene",
            parameters=config["lights"],
            room_id=room_id,
        )
        self.execute_command(light_cmd)

        audio_cfg = config.get("audio", {})
        if audio_cfg:
            audio_cmd = ActuationCommand(
                domain="audio",
                target_id=f"speaker_{room_id}",
                action=audio_cfg.get("action", "play"),
                parameters={"track": audio_cfg.get("track"), "volume": audio_cfg.get("volume")},
                room_id=room_id,
            )
            self.execute_command(audio_cmd)

        return {
            "status": "scene_applied",
            "scene": scene_name,
            "room_id": room_id,
            "state": self.active_room_states.get(room_id),
        }


physical_actuator = UnifiedPhysicalActuationBridge()
