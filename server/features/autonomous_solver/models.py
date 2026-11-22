from enum import Enum
from typing import Any, Dict, List, Optional
import time
from pydantic import BaseModel, Field


class TargetOS(str, Enum):
    AUTO = "auto"
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    EMBEDDED = "embedded"


class ScriptArtifact(BaseModel):
    filename: str = Field(..., min_length=1, max_length=128)
    language: str = Field("python", pattern="^(python|bash|sh|powershell|batch|text)$")
    content: str
    executable: bool = True
    purpose: str = ""


class CommandStep(BaseModel):
    step_id: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    command: str = Field(..., min_length=1, max_length=4096)
    timeout_seconds: float = Field(60.0, ge=1.0, le=600.0)
    expected_exit_code: int = 0
    verify_stdout_contains: Optional[str] = None


class ExecutionPlan(BaseModel):
    summary: str = ""
    target_os: TargetOS = TargetOS.AUTO
    scripts: List[ScriptArtifact] = Field(default_factory=list)
    commands: List[CommandStep] = Field(default_factory=list)
    verification_command: Optional[str] = None


class CommandExecutionRecord(BaseModel):
    step_id: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    duration_ms: float


class DiagnosticFinding(BaseModel):
    category: str
    root_cause: str
    suggested_fix_strategy: str
    extracted_symbol: str = ""


class AttemptRecord(BaseModel):
    attempt_number: int
    plan_summary: str
    scripts_written: List[str] = Field(default_factory=list)
    command_results: List[CommandExecutionRecord] = Field(default_factory=list)
    diagnostics: List[DiagnosticFinding] = Field(default_factory=list)
    healing_action: str = ""
    succeeded: bool = False
    duration_ms: float = 0.0


class AutonomousSolveRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=4000)
    user_id: str = Field("user_primary", min_length=1, max_length=64)
    target_os: TargetOS = TargetOS.AUTO
    target_host: Optional[str] = None
    target_port: int = Field(22, ge=1, le=65535)
    target_user: str = "root"
    ssh_vault_entry_id: Optional[str] = None
    max_iterations: int = Field(5, ge=1, le=10)
    initial_plan: Optional[ExecutionPlan] = None
    dry_run: bool = False


class AutonomousSolveResult(BaseModel):
    job_id: str
    goal: str
    resolved_os: TargetOS
    target: str
    success: bool
    iterations_used: int
    workspace_dir: str
    attempts: List[AttemptRecord] = Field(default_factory=list)
    final_output: str = ""
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
