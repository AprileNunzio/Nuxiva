from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any
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
class CEOAdvisoryVerdict:
    feasibility_score: float = 0.95
    identified_risks: list[str] = field(default_factory=list)
    mandatory_guidelines: list[str] = field(default_factory=list)
    recommended_modularity: str = ""
    architecture_pattern: str = "Clean Architecture & Feature Colocation"

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasibility_score": self.feasibility_score,
            "identified_risks": list(self.identified_risks),
            "mandatory_guidelines": list(self.mandatory_guidelines),
            "recommended_modularity": self.recommended_modularity,
            "architecture_pattern": self.architecture_pattern,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CEOAdvisoryVerdict":
        if not isinstance(data, dict):
            return cls()
        return cls(
            feasibility_score=float(data.get("feasibility_score", 0.95)),
            identified_risks=[str(r) for r in data.get("identified_risks", []) if r],
            mandatory_guidelines=[str(g) for g in data.get("mandatory_guidelines", []) if g],
            recommended_modularity=str(data.get("recommended_modularity", "")),
            architecture_pattern=str(
                data.get("architecture_pattern", "Clean Architecture & Feature Colocation")
            ),
        )


@dataclass
class ReasoningStep:
    step_index: int
    thought: str
    doubt: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_output: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "thought": self.thought,
            "doubt": self.doubt,
            "tool_name": self.tool_name,
            "tool_args": dict(self.tool_args),
            "tool_output": self.tool_output,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReasoningStep":
        return cls(
            step_index=int(data.get("step_index", 1)),
            thought=str(data.get("thought", "")),
            doubt=str(data.get("doubt", "")),
            tool_name=str(data.get("tool_name", "")),
            tool_args=dict(data.get("tool_args", {})) if isinstance(data.get("tool_args"), dict) else {},
            tool_output=str(data.get("tool_output", "")),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class AcceptanceCriteria:
    description: str
    target: str = ""
    verified: bool = False
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "target": self.target,
            "verified": self.verified,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptanceCriteria":
        return cls(
            description=str(data.get("description", "")),
            target=str(data.get("target", "")),
            verified=bool(data.get("verified", False)),
            evidence=str(data.get("evidence", "")),
        )


@dataclass
class Specialist:
    id: str
    role: str
    title: str
    mission_role: str
    capabilities: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    guidelines: str = ""
    is_dynamic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "title": self.title,
            "mission_role": self.mission_role,
            "capabilities": list(self.capabilities),
            "tools": list(self.tools),
            "guidelines": self.guidelines,
            "is_dynamic": self.is_dynamic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Specialist":
        return cls(
            id=str(data.get("id", "")),
            role=str(data.get("role", "")),
            title=str(data.get("title", "")),
            mission_role=str(data.get("mission_role", "")),
            capabilities=[str(c) for c in data.get("capabilities", [])],
            tools=[str(t) for t in data.get("tools", [])],
            guidelines=str(data.get("guidelines", "")),
            is_dynamic=bool(data.get("is_dynamic", True)),
        )


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
class MissionQuestion:
    id: str
    question: str
    options: list[str] = field(default_factory=list)
    is_multi_select: bool = False
    answered: bool = False
    answer: str = ""
    selected_options: list[str] = field(default_factory=list)
    rationale: str = ""
    asked_by: str = "CEO Architect"
    created_at: float = field(default_factory=time.time)
    answered_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "options": list(self.options),
            "is_multi_select": self.is_multi_select,
            "answered": self.answered,
            "answer": self.answer,
            "selected_options": list(self.selected_options),
            "rationale": self.rationale,
            "asked_by": self.asked_by,
            "created_at": self.created_at,
            "answered_at": self.answered_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionQuestion":
        return cls(
            id=str(data.get("id", "")),
            question=str(data.get("question", "")),
            options=[str(o) for o in data.get("options", [])],
            is_multi_select=bool(data.get("is_multi_select", False)),
            answered=bool(data.get("answered", False)),
            answer=str(data.get("answer", "")),
            selected_options=[str(o) for o in data.get("selected_options", [])],
            rationale=str(data.get("rationale", "")),
            asked_by=str(data.get("asked_by", "CEO Architect")),
            created_at=float(data.get("created_at", time.time())),
            answered_at=float(data.get("answered_at", 0.0)),
        )


@dataclass
class CollabMessage:
    id: str
    sender_id: str
    sender_role: str
    target_id: str
    channel: str
    content: str
    kind: str = "message"
    artifact_ref: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role,
            "target_id": self.target_id,
            "channel": self.channel,
            "content": self.content,
            "kind": self.kind,
            "artifact_ref": self.artifact_ref,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollabMessage":
        return cls(
            id=str(data.get("id", "")),
            sender_id=str(data.get("sender_id", "")),
            sender_role=str(data.get("sender_role", "")),
            target_id=str(data.get("target_id", "all")),
            channel=str(data.get("channel", "general")),
            content=str(data.get("content", "")),
            kind=str(data.get("kind", "message")),
            artifact_ref=str(data.get("artifact_ref", "")),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class MissionArtifact:
    id: str
    title: str
    kind: str
    relative_path: str
    checksum: str
    size_bytes: int
    generated_by: str
    diff: str = ""
    symbols: list[str] = field(default_factory=list)
    line_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "relative_path": self.relative_path,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "generated_by": self.generated_by,
            "diff": self.diff,
            "symbols": list(self.symbols),
            "line_count": self.line_count,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionArtifact":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            kind=str(data.get("kind", "file")),
            relative_path=str(data.get("relative_path", "")),
            checksum=str(data.get("checksum", "")),
            size_bytes=int(data.get("size_bytes", 0)),
            generated_by=str(data.get("generated_by", "")),
            diff=str(data.get("diff", "")),
            symbols=[str(s) for s in data.get("symbols", []) if s],
            line_count=int(data.get("line_count", 0)),
            timestamp=float(data.get("timestamp", time.time())),
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
