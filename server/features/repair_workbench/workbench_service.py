import asyncio
import os
import time
import uuid
from typing import Callable, Dict, Tuple

from server.features.project_workspace.manager import project_manager
from server.features.repair_workbench.errors import SessionAccessException
from server.features.repair_workbench.frame_pipeline import apply_observation
from server.features.repair_workbench.frame_validator import decode_frame
from server.features.repair_workbench.native_bridge import WorkbenchEngine
from server.features.repair_workbench.project_archive import ProjectArchive
from server.features.repair_workbench.session_models import WorkbenchSession
from server.features.repair_workbench.session_requests import (
    AnalyzeFrameRequest,
    StartSessionRequest,
    TeachComponentRequest,
)
from server.features.repair_workbench.session_store import EncryptedSessionStore
from server.features.repair_workbench.vision_port import VisionAnalyzer
from server.shared.errors.domain_errors import EntityNotFoundException

MIN_ANALYSIS_INTERVAL_SECONDS = 2.5


class WorkbenchService:
    def __init__(
        self,
        store: EncryptedSessionStore,
        analyzer: VisionAnalyzer,
        engine_factory: Callable[[], WorkbenchEngine] = WorkbenchEngine,
        clock: Callable[[], float] = time.time,
        archive: ProjectArchive = None,
    ) -> None:
        self._store = store
        self._analyzer = analyzer
        self._engine_factory = engine_factory
        self._clock = clock
        self._archive = archive or ProjectArchive(os.path.join(store._root, "projects"), clock=clock)
        self._cache: Dict[Tuple[str, str], WorkbenchSession] = {}
        self._engines: Dict[str, WorkbenchEngine] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_analysis: Dict[str, float] = {}

    def start(self, owner_id: str, request: StartSessionRequest) -> WorkbenchSession:
        self._require_open(owner_id, request.project_id)
        now = self._clock()
        session = WorkbenchSession(
            session_id=uuid.uuid4().hex,
            project_id=request.project_id,
            owner_id=owner_id,
            camera_id=request.camera_id or "",
            camera_name=request.camera_name,
            language=request.language,
            created_at=now,
            updated_at=now,
        )
        self._remember(session)
        return session

    def get(self, owner_id: str, session_id: str) -> WorkbenchSession:
        cached = self._cache.get((owner_id, session_id))
        if cached is not None:
            return cached
        loaded = self._store.load(owner_id, session_id)
        if loaded is None:
            raise EntityNotFoundException("workbench_session", session_id)
        if loaded.owner_id != owner_id:
            raise SessionAccessException(session_id)
        self._cache[(owner_id, session_id)] = loaded
        return loaded

    def archived_projects(self, owner_id: str, include_closed=False):
        return self._archive.list_projects(owner_id, include_closed=include_closed)

    def resume(self, owner_id: str, project_id: str) -> WorkbenchSession:
        project = project_manager.get_by_id(owner_id, project_id)
        if project is None or project.status in {"COMPLETED", "ARCHIVED", "CLOSED"}:
            raise EntityNotFoundException("open_project", project_id)
        session = self._archive.latest_session(owner_id, project_id)
        if session is None:
            raise EntityNotFoundException("workbench_project", project_id)
        self._remember(session)
        return session

    def close_project(self, owner_id: str, project_id: str) -> None:
        project = project_manager.get_by_id(owner_id, project_id)
        if project is None:
            raise EntityNotFoundException("project", project_id)
        project.status = "COMPLETED"
        project_manager.save(owner_id, project)
        self._archive.set_status(owner_id, project_id, "COMPLETED")

    async def analyze(
        self, owner_id: str, session_id: str, request: AnalyzeFrameRequest
    ) -> Tuple[WorkbenchSession, bool]:
        session = self.get(owner_id, session_id)
        self._require_open(owner_id, session.project_id)
        frame = decode_frame(request.frame_base64)
        engine = self._engine(session_id)
        if request.grid:
            session.scene_state = engine.observe_stability(request.grid)
        session.frame_count += 1
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        if lock.locked() or not self._due(session):
            return session, False
        async with lock:
            known = [c.ref for c in session.circuit.components]
            observation = await self._analyzer.analyze(frame, session.language, known)
            self._require_open(owner_id, session.project_id)
            apply_observation(session, engine, observation)
            self._last_analysis[session_id] = self._clock()
        self._remember(session)
        self._archive.save_snapshot(session, frame)
        return session, True

    def teach(
        self, owner_id: str, session_id: str, request: TeachComponentRequest
    ) -> WorkbenchSession:
        session = self.get(owner_id, session_id)
        self._require_open(owner_id, session.project_id)
        popup = next((p for p in session.popups if p.track_id == request.track_id), None)
        if popup is None:
            raise EntityNotFoundException("track", str(request.track_id))
        previous = popup.key
        for key, label in list(session.aliases.items()):
            if label == previous:
                session.aliases[key] = request.label
        session.aliases[previous] = request.label
        if request.value:
            session.taught_values[request.label] = request.value
        self._engine(session_id).relabel(request.track_id, request.label)
        popup.key = request.label
        popup.label = request.label
        popup.value = request.value or popup.value
        popup.taught = True
        self._remember(session)
        return session

    def remember(self, session: WorkbenchSession) -> None:
        self._remember(session)

    def _remember(self, session: WorkbenchSession) -> None:
        project = self._require_open(session.owner_id, session.project_id)
        session.updated_at = self._clock()
        self._archive.save_session(session, project_name=project.name, status=project.status)
        self._cache[(session.owner_id, session.session_id)] = session
        self._store.save(session)

    @staticmethod
    def _require_open(owner_id: str, project_id: str):
        project = project_manager.get_by_id(owner_id, project_id)
        if project is None or project.status.upper() in {"COMPLETED", "ARCHIVED", "CLOSED"}:
            raise EntityNotFoundException("open_project", project_id)
        return project

    def _engine(self, session_id: str) -> WorkbenchEngine:
        engine = self._engines.get(session_id)
        if engine is None:
            engine = self._engine_factory()
            self._engines[session_id] = engine
        return engine

    def _due(self, session: WorkbenchSession) -> bool:
        if session.scene_state == "operator_working":
            return False
        elapsed = self._clock() - self._last_analysis.get(session.session_id, 0.0)
        return elapsed >= MIN_ANALYSIS_INTERVAL_SECONDS
