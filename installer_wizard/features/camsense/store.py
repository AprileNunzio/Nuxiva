import json
import os
import threading
import time

from config import STATE_DIR

from features.camsense.model import MAX_LABELS, MAX_SAMPLES, MAX_SENSORS, SenseError

FILE = STATE_DIR / "camsense.json"


class SensorStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()

    def all(self) -> dict[str, dict]:
        try:
            data = json.loads(FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, rows: dict[str, dict]) -> None:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False)
        os.replace(tmp, FILE)

    def get(self, sensor_id: str) -> dict:
        row = self.all().get(sensor_id)
        if row is None:
            raise SenseError("not_found", 404)
        return row

    def create(self, sensor_id: str, name: str, camera: str, area: list[float]) -> dict:
        with self.lock:
            rows = self.all()
            if sensor_id in rows:
                raise SenseError("already_exists", 409)
            if len(rows) >= MAX_SENSORS:
                raise SenseError("limit_reached", 409)
            rows[sensor_id] = {"id": sensor_id, "name": name, "camera": camera, "region": area, "samples": {}, "state": "", "confidence": 0.0,
                               "reason": "", "since": 0.0, "checked": 0.0, "pending": {"label": "", "count": 0}, "created": time.time()}
            self.save(rows)
            return rows[sensor_id]

    def update(self, sensor_id: str, change) -> dict:
        with self.lock:
            rows = self.all()
            if sensor_id not in rows:
                raise SenseError("not_found", 404)
            change(rows[sensor_id])
            self.save(rows)
            return rows[sensor_id]

    def add_sample(self, sensor_id: str, label: str, vector: list[float]) -> dict:
        def change(row: dict) -> None:
            samples = row["samples"]
            if label not in samples and len(samples) >= MAX_LABELS:
                raise SenseError("limit_reached", 409)
            bucket = samples.setdefault(label, [])
            bucket.append(vector)
            del bucket[:-MAX_SAMPLES]
        return self.update(sensor_id, change)

    def remove(self, sensor_id: str) -> None:
        with self.lock:
            rows = self.all()
            if rows.pop(sensor_id, None) is None:
                raise SenseError("not_found", 404)
            self.save(rows)


sensors = SensorStore()
