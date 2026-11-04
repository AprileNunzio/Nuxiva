import json
import os
import re
from pathlib import Path

from config import STATE_DIR
from sealed import SealedFile

ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


class ProjectMemory:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or STATE_DIR / "agency"

    def _file(self, project_id: str) -> SealedFile:
        if not ID.fullmatch(project_id):
            raise KeyError(project_id)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        return SealedFile(self.directory / f"{project_id}.sealed", self.directory / "memory.key")

    def load(self, project_id: str) -> dict:
        return self._file(project_id).load()

    def save(self, project_id: str, data: dict) -> None:
        self._file(project_id).save(json.loads(json.dumps(data, ensure_ascii=False)))

    def update(self, project_id: str, **changes) -> dict:
        data = self.load(project_id)
        data.update(changes)
        self.save(project_id, data)
        return data


memory = ProjectMemory()
