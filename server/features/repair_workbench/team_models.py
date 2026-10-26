"""Persisted, inspectable work orders; no hidden reasoning or inferred measurements."""
from typing import Annotated, List, Literal

from pydantic import BaseModel, Field

from server.features.repair_workbench.text_types import Identifier, LongText, MediumText

TaskStatus = Literal["idle", "running", "completed", "blocked", "failed"]
IssueTitle = Annotated[LongText, Field(max_length=500)]


class WorkbenchIssue(BaseModel):
    id: Identifier
    title: IssueTitle
    source: Literal["operator", "observation"] = "operator"
    severity: Literal["low", "medium", "high"] = "medium"
    status: Literal["open", "resolved"] = "open"
    created_at: float
    updated_at: float = 0
    resolution: LongText = ""


class TeamEvidence(BaseModel):
    url: str = Field(max_length=2048, pattern=r"^https?://")
    title: MediumText = ""


class WorkerResult(BaseModel):
    status: Literal["completed", "blocked"] = "completed"
    summary: LongText = ""
    evidence: List[TeamEvidence] = Field(default_factory=list, max_length=12)


class TeamWorker(BaseModel):
    id: Identifier
    status: TaskStatus = "idle"
    task_id: str = ""
    summary: LongText = ""
    updated_at: float = 0


class TeamTask(BaseModel):
    id: Identifier
    worker_id: Identifier
    issue_ids: List[Identifier] = Field(default_factory=list)
    status: TaskStatus = "running"
    summary: LongText = ""
    evidence: List[TeamEvidence] = Field(default_factory=list)
    created_at: float
    updated_at: float


class WorkbenchTeam(BaseModel):
    workers: List[TeamWorker] = Field(default_factory=list)
    issues: List[WorkbenchIssue] = Field(default_factory=list)
    tasks: List[TeamTask] = Field(default_factory=list)
    running: bool = False
    last_context_key: str = Field(default="", max_length=64)
    last_run_at: float = 0


class CreateIssueRequest(BaseModel):
    title: IssueTitle = Field(min_length=2)
    severity: Literal["low", "medium", "high"] = "medium"


class UpdateIssueRequest(BaseModel):
    status: Literal["open", "resolved"]
    resolution: LongText = ""


class RunTeamRequest(BaseModel):
    message: LongText = ""
