from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any

from features.autonomous_worker.domain.entities import (
    AcceptanceCriteria,
    ArtifactRevision,
    CEOAdvisoryVerdict,
    CollabMessage,
    MissionArtifact,
    MissionQuestion,
    ReasoningStep,
    Specialist,
)
from features.autonomous_worker.domain.memory import EpisodicMemory


class MissionStatus(str, Enum):
    PLANNING = "planning"
    QUESTION = "question"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    REVIEW = "review"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    phase_id: str
    title: str
    description: str
    specialist_id: str = ""
    specialist_role: str = ""
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    round: int = 1
    feedback: str = ""
    criteria: list[AcceptanceCriteria] = field(default_factory=list)
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    doubts: list[str] = field(default_factory=list)
    ceo_review_notes: list[str] = field(default_factory=list)
    result: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phase_id": self.phase_id,
            "title": self.title,
            "description": self.description,
            "specialist_id": self.specialist_id,
            "specialist_role": self.specialist_role,
            "depends_on": list(self.depends_on),
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "round": self.round,
            "feedback": self.feedback,
            "criteria": [c.to_dict() for c in self.criteria],
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "doubts": list(self.doubts),
            "ceo_review_notes": list(self.ceo_review_notes),
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        raw_status = data.get("status", TaskStatus.PENDING.value)
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.PENDING
        return cls(
            id=str(data.get("id", "")),
            phase_id=str(data.get("phase_id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            specialist_id=str(data.get("specialist_id", "")),
            specialist_role=str(data.get("specialist_role", "")),
            depends_on=[str(d) for d in data.get("depends_on", [])],
            status=status,
            round=int(data.get("round", 1)),
            feedback=str(data.get("feedback", "")),
            criteria=[
                AcceptanceCriteria.from_dict(c)
                for c in data.get("criteria", [])
                if isinstance(c, dict)
            ],
            reasoning_steps=[
                ReasoningStep.from_dict(s)
                for s in data.get("reasoning_steps", [])
                if isinstance(s, dict)
            ],
            doubts=[str(d) for d in data.get("doubts", []) if d],
            ceo_review_notes=[str(n) for n in data.get("ceo_review_notes", []) if n],
            result=str(data.get("result", "")),
            error=str(data.get("error", "")),
            started_at=float(data.get("started_at", 0.0)),
            completed_at=float(data.get("completed_at", 0.0)),
        )


@dataclass
class Phase:
    id: str
    title: str
    description: str
    tasks: list[Task] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Phase":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            tasks=[Task.from_dict(t) for t in data.get("tasks", []) if isinstance(t, dict)],
            status=str(data.get("status", "pending")),
        )


@dataclass
class Mission:
    id: str
    title: str
    goal: str
    domain: str
    lang: str = "it"
    directives: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    phases: list[Phase] = field(default_factory=list)
    specialists: list[Specialist] = field(default_factory=list)
    questions: list[MissionQuestion] = field(default_factory=list)
    collab_messages: list[CollabMessage] = field(default_factory=list)
    artifacts: list[MissionArtifact] = field(default_factory=list)
    memory: EpisodicMemory = field(default_factory=EpisodicMemory)
    council_verdict: CEOAdvisoryVerdict = field(default_factory=CEOAdvisoryVerdict)
    status: MissionStatus = MissionStatus.PLANNING
    progress: int = 0
    error: str = ""
    workspace: str = ""
    final_review_rounds: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def all_tasks(self) -> list[Task]:
        return [task for phase in self.phases for task in phase.tasks]

    def recalculate_progress(self) -> int:
        tasks = self.all_tasks()
        if not tasks:
            self.progress = 100 if self.status == MissionStatus.DONE else 0
            return self.progress
        done_count = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        self.progress = int(round((done_count / len(tasks)) * 100))
        return self.progress

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "domain": self.domain,
            "lang": self.lang,
            "directives": list(self.directives),
            "options": dict(self.options),
            "phases": [p.to_dict() for p in self.phases],
            "specialists": [s.to_dict() for s in self.specialists],
            "questions": [q.to_dict() for q in self.questions],
            "collab_messages": [m.to_dict() for m in self.collab_messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "memory": self.memory.to_dict(),
            "council_verdict": self.council_verdict.to_dict(),
            "status": self.status.value if isinstance(self.status, MissionStatus) else str(self.status),
            "progress": self.progress,
            "error": self.error,
            "workspace": self.workspace,
            "final_review_rounds": self.final_review_rounds,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        raw_status = data.get("status", MissionStatus.PLANNING.value)
        try:
            status = MissionStatus(raw_status)
        except ValueError:
            status = MissionStatus.PLANNING
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            goal=str(data.get("goal", "")),
            domain=str(data.get("domain", "general")),
            lang=str(data.get("lang", "it")),
            directives=[str(d) for d in data.get("directives", [])],
            options=dict(data.get("options", {})),
            phases=[Phase.from_dict(p) for p in data.get("phases", []) if isinstance(p, dict)],
            specialists=[Specialist.from_dict(s) for s in data.get("specialists", []) if isinstance(s, dict)],
            questions=[MissionQuestion.from_dict(q) for q in data.get("questions", []) if isinstance(q, dict)],
            collab_messages=[CollabMessage.from_dict(m) for m in data.get("collab_messages", []) if isinstance(m, dict)],
            artifacts=[MissionArtifact.from_dict(a) for a in data.get("artifacts", []) if isinstance(a, dict)],
            memory=EpisodicMemory.from_dict(data.get("memory", {})) if isinstance(data.get("memory"), dict) else EpisodicMemory(),
            council_verdict=CEOAdvisoryVerdict.from_dict(data.get("council_verdict", {})) if isinstance(data.get("council_verdict"), dict) else CEOAdvisoryVerdict(),
            status=status,
            progress=int(data.get("progress", 0)),
            error=str(data.get("error", "")),
            workspace=str(data.get("workspace", "")),
            final_review_rounds=int(data.get("final_review_rounds", 0)),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
        )


__all__ = [
    "AcceptanceCriteria",
    "ArtifactRevision",
    "CEOAdvisoryVerdict",
    "CollabMessage",
    "Mission",
    "MissionArtifact",
    "MissionQuestion",
    "MissionStatus",
    "Phase",
    "ReasoningStep",
    "Specialist",
    "Task",
    "TaskStatus",
]
