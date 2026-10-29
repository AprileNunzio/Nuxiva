import json
import time
from pathlib import Path

from features.hardware.atomic import write_text


class ManagedDevices:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("devices"), dict):
            raise ValueError("Invalid managed hardware registry")
        return data["devices"]

    def record(self, device):
        records = self.load()
        records[device.id] = {"checked_at": time.time(), "packages": list(device.required_packages),
                              "status": device.status}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = dict(sorted(records.items(), key=lambda item: item[1]["checked_at"])[-256:])
        write_text(self.path, json.dumps({"version": 1, "devices": records}, ensure_ascii=False))

    def due(self, device_id, interval=86400):
        record = self.load().get(device_id)
        return bool(record and time.time() - record["checked_at"] >= interval and record["packages"])
