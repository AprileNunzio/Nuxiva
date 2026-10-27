from dataclasses import dataclass, field
import time
from typing import Any


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
class ArtifactRevision:
    version: int
    checksum: str
    diff: str = ""
    line_count: int = 0
    size_bytes: int = 0
    generated_by: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "checksum": self.checksum,
            "diff": self.diff,
            "line_count": self.line_count,
            "size_bytes": self.size_bytes,
            "generated_by": self.generated_by,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRevision":
        return cls(
            version=int(data.get("version", 1)),
            checksum=str(data.get("checksum", "")),
            diff=str(data.get("diff", "")),
            line_count=int(data.get("line_count", 0)),
            size_bytes=int(data.get("size_bytes", 0)),
            generated_by=str(data.get("generated_by", "")),
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
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    version: int = 1
    revisions: list[ArtifactRevision] = field(default_factory=list)
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
            "imports": list(self.imports),
            "line_count": self.line_count,
            "version": self.version,
            "revisions": [r.to_dict() for r in self.revisions],
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
            imports=[str(i) for i in data.get("imports", []) if i],
            line_count=int(data.get("line_count", 0)),
            version=int(data.get("version", 1)),
            revisions=[
                ArtifactRevision.from_dict(r)
                for r in data.get("revisions", [])
                if isinstance(r, dict)
            ],
            timestamp=float(data.get("timestamp", time.time())),
        )
