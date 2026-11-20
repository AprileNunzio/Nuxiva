import time
from dataclasses import dataclass, field
from typing import Any

from agenti.agency.circadian import resolve_circadian_context
from agenti.people import people


@dataclass
class AmbientSensorReading:
    sensor_id: str
    kind: str
    value: float
    unit: str
    room_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class PresenceSignal:
    source_kind: str
    detected_slug: str | None
    confidence: float
    room_id: str
    raw_payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AmbientSensorFusionGovernor:
    def __init__(self) -> None:
        self.active_rooms: dict[str, dict[str, Any]] = {}
        self.sensor_readings: list[AmbientSensorReading] = []
        self.presence_history: list[PresenceSignal] = []

    def ingest_presence_signal(self, signal: PresenceSignal) -> dict[str, Any]:
        self.presence_history.append(signal)
        room_data = self.active_rooms.setdefault(signal.room_id, {
            "room_id": signal.room_id,
            "occupants": set(),
            "dominant_person": None,
            "last_motion_ts": time.time(),
        })

        if signal.detected_slug and signal.confidence >= 0.70:
            p = people.load(signal.detected_slug)
            if p:
                room_data["occupants"].add(signal.detected_slug)
                room_data["dominant_person"] = signal.detected_slug
                room_data["last_motion_ts"] = signal.timestamp

        return {
            "room_id": signal.room_id,
            "occupants": sorted(list(room_data["occupants"])),
            "dominant_person": room_data["dominant_person"],
            "circadian": resolve_circadian_context(
                person_slug=room_data["dominant_person"],
                co_present_slugs=list(room_data["occupants"]),
            ),
        }

    def ingest_sensor_reading(self, reading: AmbientSensorReading) -> dict[str, Any]:
        self.sensor_readings.append(reading)
        if len(self.sensor_readings) > 1000:
            self.sensor_readings = self.sensor_readings[-500:]

        room_data = self.active_rooms.setdefault(reading.room_id, {
            "room_id": reading.room_id,
            "occupants": set(),
            "dominant_person": None,
            "last_motion_ts": time.time(),
        })
        metrics = room_data.setdefault("metrics", {})
        metrics[reading.kind] = {
            "sensor_id": reading.sensor_id,
            "value": reading.value,
            "unit": reading.unit,
            "updated_at": reading.timestamp,
        }
        return {"status": "recorded", "room_id": reading.room_id, "kind": reading.kind, "value": reading.value}

    def get_room_state(self, room_id: str) -> dict[str, Any]:
        data = self.active_rooms.get(room_id, {
            "room_id": room_id,
            "occupants": set(),
            "dominant_person": None,
            "metrics": {},
            "last_motion_ts": 0.0,
        })
        occupants_list = sorted(list(data["occupants"]))
        dominant = data["dominant_person"]
        return {
            "room_id": room_id,
            "occupants": occupants_list,
            "dominant_person": dominant,
            "metrics": data.get("metrics", {}),
            "circadian": resolve_circadian_context(
                person_slug=dominant,
                co_present_slugs=occupants_list,
            ),
            "is_occupied": len(occupants_list) > 0,
        }

    def clear_room_occupancy(self, room_id: str) -> None:
        if room_id in self.active_rooms:
            self.active_rooms[room_id]["occupants"].clear()
            self.active_rooms[room_id]["dominant_person"] = None


ambient_fusion = AmbientSensorFusionGovernor()
