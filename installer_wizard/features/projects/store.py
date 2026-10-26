import json
import logging
import threading
import time

from config import STATE_DIR
from sealed import write_private

from features.projects.model import MAX_PROJECTS, Project, ProjectError, restore

log = logging.getLogger("nuxiva.projects")
FILE = STATE_DIR / "projects.json"


class ProjectStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, Project] | None = None

    def _load(self) -> dict[str, Project]:
        if self._items is not None:
            return self._items
        try:
            rows = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []
        except (OSError, ValueError) as exc:
            log.error("Progetti non leggibili: %s", exc)
            raise
        items: dict[str, Project] = {}
        for row in rows if isinstance(rows, list) else []:
            try:
                project = restore(row)
            except ProjectError as exc:
                log.warning("Progetto scartato: %s", exc)
                continue
            for step in project.steps:
                if step.status == "running":
                    step.status = "pending"
            items[project.id] = project
        self._items = items
        return items

    def _save(self) -> None:
        data = [p.to_dict() for p in self._load().values()]
        write_private(FILE, json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))

    def all(self) -> list[Project]:
        with self._lock:
            return sorted(self._load().values(), key=lambda p: p.created)

    def get(self, project_id: str) -> Project:
        with self._lock:
            found = self._load().get(project_id)
        if found is None:
            raise KeyError(project_id)
        return found

    def add(self, project: Project) -> Project:
        with self._lock:
            items = self._load()
            if len([p for p in items.values() if p.status in ("planning", "running", "paused")]) >= MAX_PROJECTS:
                raise ProjectError("Numero massimo di progetti aperti raggiunto")
            items[project.id] = project
            self._save()
            return project

    def save(self, project: Project) -> None:
        with self._lock:
            project.updated = time.time()
            self._load()[project.id] = project
            self._save()

    def remove(self, project_id: str) -> None:
        with self._lock:
            items = self._load()
            if project_id not in items:
                raise KeyError(project_id)
            del items[project_id]
            self._save()


projects = ProjectStore()
