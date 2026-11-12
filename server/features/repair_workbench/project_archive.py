"""Owner-scoped, encrypted project dossiers, independent of the active camera.

Snapshots are evidence, never an assertion of board identity. Reopening a project
uses its explicit project identifier; changing cameras cannot silently merge work.
"""
import hashlib
import logging
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Optional

from server.config.env import settings
from server.features.repair_workbench.session_models import WorkbenchSession
from server.features.repair_workbench.session_store import _cipher

SCHEMA_VERSION = 1
MAX_SNAPSHOTS = 60
MAX_SNAPSHOT_BYTES = 4_500_000
SNAPSHOT_INTERVAL = 30.0
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,63}\Z")
_CLOSED = {"COMPLETED", "ARCHIVED", "CLOSED"}
_LOG = logging.getLogger(__name__)


class ProjectArchive:
    def __init__(self, root: Optional[str] = None, clock=time.time):
        self.root = Path(root or os.path.join(settings.DATA_DIR, "projects"))
        self.clock = clock
        self._lock = threading.RLock()

    def _directory(self, owner_id: str, project_id: str, create=True) -> Path:
        for identifier in (owner_id, project_id):
            if not _IDENTIFIER.fullmatch(identifier):
                raise ValueError("Invalid project archive identifier")
        path = self.root / owner_id / project_id / "repair"
        # Reject symlink escapes, including a pre-existing parent directory.
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("Project archive path escapes storage")
        if create:
            for folder in ("sessions", "images", "schematics", "tasks", "sources", "logs"):
                child = path / folder
                if not child.resolve().is_relative_to(path.resolve()):
                    raise ValueError("Project archive folder escapes storage")
                child.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        if path.is_symlink():
            raise ValueError("Project archive does not follow file links")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temporary = handle.name
                handle.write(_cipher().encrypt(data))
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.remove(temporary)

    @staticmethod
    def _read(path: Path):
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("Project archive does not follow file links")
        return json.loads(_cipher().decrypt(path.read_bytes()))

    def _manifest(self, directory: Path, owner_id: str, project_id: str):
        path = directory / "manifest.enc"
        if path.exists():
            manifest = self._read(path)
            if manifest.get("owner_id") != owner_id or manifest.get("project_id") != project_id:
                raise ValueError("Project archive identity mismatch")
            if manifest.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Unsupported project archive schema")
            required = {"name", "status", "created_at", "updated_at", "latest_session_id", "snapshots", "event_count"}
            if not required.issubset(manifest) or manifest["status"] not in {"ACTIVE", "PAUSED", *_CLOSED}:
                raise ValueError("Invalid project archive manifest")
            if not isinstance(manifest["updated_at"], (int, float)):
                raise ValueError("Invalid project archive timestamp")
            return manifest
        return {"schema_version": SCHEMA_VERSION, "owner_id": owner_id,
                "project_id": project_id, "name": "", "status": "ACTIVE",
                "created_at": self.clock(), "updated_at": self.clock(),
                "latest_session_id": "", "snapshots": [], "event_count": 0}

    def _save_manifest(self, directory: Path, manifest):
        self._write(directory / "manifest.enc", json.dumps(manifest).encode())

    def save_session(self, session: WorkbenchSession, project_name: str = "", status=None):
        with self._lock:
            directory = self._directory(session.owner_id, session.project_id)
            manifest = self._manifest(directory, session.owner_id, session.project_id)
            if manifest["status"] in _CLOSED:
                raise ValueError("Project archive is closed")
            if not _IDENTIFIER.fullmatch(session.session_id):
                raise ValueError("Invalid session identifier")
            if project_name:
                manifest["name"] = project_name[:500]
            if status is not None:
                if str(status).upper() not in {"ACTIVE", "PAUSED", *_CLOSED}:
                    raise ValueError("Invalid project status")
                manifest["status"] = str(status).upper()
            self._write(directory / "sessions" / f"{session.session_id}.enc",
                        session.model_dump_json().encode())
            # A delayed response from an older session remains historical; it must
            # never replace the active session's dossier or task state.
            current = manifest.get("latest_session_id")
            if current and current != session.session_id:
                previous = self._read(directory / "sessions" / f"{current}.enc")
                if previous["created_at"] > session.created_at:
                    return
            manifest.update(updated_at=self.clock(), latest_session_id=session.session_id)
            self._write(directory / "schematics" / "latest.enc", session.circuit.model_dump_json().encode())
            team = session.team.model_dump(mode="json")
            self._write(directory / "tasks" / "latest.enc", json.dumps(team).encode())
            sources = [dict(source, task_id=task["id"], worker_id=task["worker_id"])
                       for task in team.get("tasks", []) for source in task.get("evidence", [])]
            self._write(directory / "sources" / "latest.enc", json.dumps(sources).encode())
            # Record changed observable evidence, not private model reasoning.
            summary = {"dossier": session.dossier.model_dump(mode="json"),
                       "advice": [item.model_dump(mode="json") for item in session.advice],
                       "notes": [item.model_dump(mode="json") for item in session.notes],
                       "team": team, "model": session.vision_model}
            digest = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()
            if digest != manifest.get("last_event_digest"):
                section_digests = {key: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                                   for key, value in summary.items()}
                changed = {key: value for key, value in summary.items()
                           if section_digests[key] != manifest.get("section_digests", {}).get(key)}
                event_id = manifest["event_count"] + 1
                self._write(directory / "logs" / f"{event_id:06d}.enc", json.dumps({
                    "schema_version": SCHEMA_VERSION, "timestamp": self.clock(),
                    "session_id": session.session_id, "evidence": changed}).encode())
                manifest.update(event_count=event_id, last_event_digest=digest,
                                section_digests=section_digests)
            self._save_manifest(directory, manifest)

    def save_snapshot(self, session: WorkbenchSession, frame: bytes):
        if not frame or len(frame) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Invalid snapshot size")
        if not frame.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
            raise ValueError("Invalid snapshot format")
        with self._lock:
            directory = self._directory(session.owner_id, session.project_id)
            manifest = self._manifest(directory, session.owner_id, session.project_id)
            if manifest["status"] in _CLOSED:
                raise ValueError("Project archive is closed")
            digest = hashlib.sha256(frame).hexdigest()
            snapshots = manifest["snapshots"]
            if any(item["sha256"] == digest for item in snapshots):
                return None
            if len(snapshots) >= MAX_SNAPSHOTS or (snapshots and self.clock() - snapshots[-1]["timestamp"] < SNAPSHOT_INTERVAL):
                return None
            name = f"{digest}.enc"
            self._write(directory / "images" / name, frame)
            record = {"sha256": digest, "file": f"images/{name}", "timestamp": self.clock(),
                      "session_id": session.session_id, "camera_id": session.camera_id,
                      "mime_type": "image/png" if frame.startswith(b"\x89PNG") else "image/jpeg"}
            snapshots.append(record)
            self._save_manifest(directory, manifest)
            return record

    def list_projects(self, owner_id: str, include_closed=False):
        self._directory(owner_id, "validation", create=False)
        projects = []
        with self._lock:
            for path in (self.root / owner_id).glob("*/repair/manifest.enc"):
                project_id = path.parent.parent.name
                try:
                    directory = self._directory(owner_id, project_id, create=False)
                    manifest = self._manifest(directory, owner_id, project_id)
                except Exception:
                    _LOG.warning("Skipping unreadable repair archive %s", project_id)
                    continue
                if include_closed or manifest["status"] not in _CLOSED:
                    projects.append({key: manifest[key] for key in (
                        "schema_version", "project_id", "name", "status", "created_at",
                        "updated_at", "latest_session_id", "event_count")})
            return sorted(projects, key=lambda item: item["updated_at"], reverse=True)

    def latest_session(self, owner_id: str, project_id: str):
        with self._lock:
            directory = self._directory(owner_id, project_id, create=False)
            manifest = self._manifest(directory, owner_id, project_id)
            session_id = manifest.get("latest_session_id")
            if not session_id:
                return None
            if not _IDENTIFIER.fullmatch(session_id):
                raise ValueError("Invalid archived session identifier")
            session = WorkbenchSession.model_validate(self._read(directory / "sessions" / f"{session_id}.enc"))
            if (session.owner_id, session.project_id) != (owner_id, project_id):
                raise ValueError("Archived session identity mismatch")
            return session

    def set_status(self, owner_id: str, project_id: str, status: str):
        if status.upper() not in {"ACTIVE", "PAUSED", *_CLOSED}:
            raise ValueError("Invalid project status")
        with self._lock:
            directory = self._directory(owner_id, project_id)
            manifest = self._manifest(directory, owner_id, project_id)
            if manifest["status"] in _CLOSED and status.upper() not in _CLOSED:
                raise ValueError("Closed project cannot be reopened implicitly")
            manifest.update(status=status.upper(), updated_at=self.clock())
            self._save_manifest(directory, manifest)
