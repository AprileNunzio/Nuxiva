import json
from pathlib import Path
import threading
import time

from config import STATE_DIR
from backend.sealed import SealedFile, write_private
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import Mission, MissionStatus
from features.autonomous_worker.domain.sanitizer import validate_identifier

DATA_DIR = STATE_DIR / "autonomous_missions"
SEALED_FILE = DATA_DIR / "missions.sealed"
KEY_FILE = DATA_DIR / "missions.key"
INDEX_FILE = DATA_DIR / "index.json"


class MissionStore:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sealed_file = self.data_dir / "missions.sealed"
        self.key_file = self.data_dir / "missions.key"
        self.index_file = self.data_dir / "index.json"
        self._lock = threading.RLock()
        self._sealed = SealedFile(self.sealed_file, self.key_file)
        self._cache: dict[str, Mission] | None = None

    def _load_all(self) -> dict[str, Mission]:
        if self._cache is not None:
            return self._cache
        missions: dict[str, Mission] = {}
        with self._lock:
            data = self._sealed.load()
            if isinstance(data, dict):
                for mid, mdata in data.items():
                    if isinstance(mdata, dict):
                        try:
                            missions[mid] = Mission.from_dict(mdata)
                        except (TypeError, ValueError, KeyError):
                            continue
            self._cache = missions
            return missions

    def _persist(self) -> None:
        if self._cache is None:
            return
        payload = {mid: m.to_dict() for mid, m in self._cache.items()}
        self._sealed.save(payload)
        index = [
            {
                "id": m.id,
                "title": m.title,
                "domain": m.domain,
                "status": m.status.value if isinstance(m.status, MissionStatus) else str(m.status),
                "progress": m.progress,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in sorted(self._cache.values(), key=lambda x: x.created_at, reverse=True)
        ]
        write_private(self.index_file, json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8"))

    def save(self, mission: Mission) -> Mission:
        validate_identifier(mission.id, "mission_id")
        mission.updated_at = time.time()
        mission.recalculate_progress()
        with self._lock:
            cached = self._load_all()
            cached[mission.id] = mission
            self._persist()
        return mission

    def get(self, mission_id: str) -> Mission:
        clean_id = validate_identifier(mission_id, "mission_id")
        with self._lock:
            cached = self._load_all()
            if clean_id not in cached:
                raise MissionNotFoundError(f"Mission {clean_id} not found")
            return cached[clean_id]

    def find(self, mission_id: str) -> Mission | None:
        try:
            return self.get(mission_id)
        except (MissionNotFoundError, MissionValidationError):
            return None

    def all(self) -> list[Mission]:
        with self._lock:
            cached = self._load_all()
            return sorted(cached.values(), key=lambda m: m.created_at, reverse=True)

    def active(self) -> list[Mission]:
        with self._lock:
            return [
                m for m in self.all()
                if m.status in (MissionStatus.PLANNING, MissionStatus.QUESTION, MissionStatus.RUNNING)
            ]

    def remove(self, mission_id: str) -> None:
        clean_id = validate_identifier(mission_id, "mission_id")
        with self._lock:
            cached = self._load_all()
            if clean_id in cached:
                del cached[clean_id]
                self._persist()


mission_store = MissionStore()
