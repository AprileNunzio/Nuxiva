import asyncio
import os
import platform
import time
import uuid
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from server.features.autonomous_solver.log_diagnostics import log_diagnostic_engine
from server.features.autonomous_solver.models import (
    AttemptRecord,
    AutonomousSolveRequest,
    AutonomousSolveResult,
    CommandExecutionRecord,
    CommandStep,
    DiagnosticFinding,
    ExecutionPlan,
    ScriptArtifact,
    TargetOS,
)
from server.features.autonomous_solver.plan_healer import (
    heal_plan_default,
    synthesize_default_plan,
)
from server.features.autonomous_solver.safety_guard import (
    SafetyViolationError,
    safe_script_path,
    validate_command_safety,
)
from server.features.device_provisioner.debian_provisioner import debian_provisioner
from server.features.device_provisioner.models import DebianProbeRequest

DEFAULT_RUNS_DIR = Path(__file__).resolve().parents[3] / "data" / "solver_runs"

PlannerFn = Callable[[AutonomousSolveRequest, TargetOS], Awaitable[ExecutionPlan]]
HealerFn = Callable[
    [AutonomousSolveRequest, TargetOS, ExecutionPlan, AttemptRecord],
    Awaitable[Tuple[ExecutionPlan, str]],
]


def detect_local_os() -> TargetOS:
    sys_name = platform.system().lower()
    if "windows" in sys_name:
        return TargetOS.WINDOWS
    if "darwin" in sys_name:
        return TargetOS.MACOS
    return TargetOS.LINUX


class UniversalAutonomousSolver:
    """
    Motore universale e cross-OS di risoluzione autonoma dei problemi:
    1. Rileva il sistema operativo target (Linux, Windows, macOS, Embedded) in locale o via SSH.
    2. Sintetizza un piano multi-script (Python / Bash / PowerShell) + comandi + verifica finale.
    3. Materializza gli script in una workspace isolata (o li trasferisce sul server remoto).
    4. Esegue i comandi, analizza i log (stdout/stderr/exit_code) con LogDiagnosticEngine.
    5. In caso di errore, applica auto-riparazione (LLM + regole deterministiche cross-OS),
       aggiorna gli script/comandi e riesegue fino al successo o al limite massimo di iterazioni.
    """

    def __init__(
        self,
        runs_dir: Optional[Path] = None,
        planner_fn: Optional[PlannerFn] = None,
        healer_fn: Optional[HealerFn] = None,
    ) -> None:
        self._runs_dir = Path(runs_dir) if runs_dir else DEFAULT_RUNS_DIR
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._planner_fn = planner_fn
        self._healer_fn = healer_fn
        self._jobs: Dict[str, AutonomousSolveResult] = {}

    def get_job(self, job_id: str) -> Optional[AutonomousSolveResult]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[AutonomousSolveResult]:
        return list(reversed(list(self._jobs.values())))[:30]

    async def solve(self, req: AutonomousSolveRequest) -> AutonomousSolveResult:
        job_id = f"solve_{uuid.uuid4().hex[:10]}"
        workspace = self._runs_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)

        resolved_os = await self._resolve_target_os(req)
        target_label = (
            f"{req.target_user}@{req.target_host}:{req.target_port}"
            if req.target_host else f"local:{resolved_os.value}"
        )

        try:
            plan = req.initial_plan or await self._synthesize_initial_plan(req, resolved_os)
        except Exception as exc:
            res = AutonomousSolveResult(
                job_id=job_id,
                goal=req.goal,
                resolved_os=resolved_os,
                target=target_label,
                success=False,
                iterations_used=0,
                workspace_dir=str(workspace),
                attempts=[],
                summary=f"Impossibile generare il piano iniziale: {exc}",
            )
            self._jobs[job_id] = res
            return res

        if req.dry_run:
            written = self._materialize_scripts(workspace, plan.scripts)
            attempt = AttemptRecord(
                attempt_number=1,
                plan_summary=plan.summary or "Dry-run plan",
                scripts_written=written,
                healing_action="dry_run_only",
                succeeded=True,
                duration_ms=0.0,
            )
            res = AutonomousSolveResult(
                job_id=job_id,
                goal=req.goal,
                resolved_os=resolved_os,
                target=target_label,
                success=True,
                iterations_used=1,
                workspace_dir=str(workspace),
                attempts=[attempt],
                final_output=f"Dry-run validato: {len(written)} script pronti, {len(plan.commands)} comandi pianificati.",
                summary=f"Piano autonomo validato per {target_label} (dry-run).",
            )
            self._jobs[job_id] = res
            return res

        attempts: List[AttemptRecord] = []
        final_output = ""
        overall_success = False

        for iteration in range(1, req.max_iterations + 1):
            t_iter = time.time()
            try:
                scripts_written = self._materialize_scripts(workspace, plan.scripts)
            except SafetyViolationError as exc:
                attempts.append(AttemptRecord(
                    attempt_number=iteration,
                    plan_summary=plan.summary,
                    diagnostics=[DiagnosticFinding(
                        category="safety_violation",
                        root_cause=str(exc),
                        suggested_fix_strategy="Rimuovere percorsi o comandi pericolosi.",
                    )],
                    succeeded=False,
                    duration_ms=round((time.time() - t_iter) * 1000, 1),
                ))
                break

            cmd_records, diagnostics, all_passed = await self._run_plan_steps(req, resolved_os, workspace, plan)

            if all_passed:
                final_output = "\n".join(r.stdout.strip() for r in cmd_records if r.stdout.strip())[-4000:]
                attempts.append(AttemptRecord(
                    attempt_number=iteration,
                    plan_summary=plan.summary,
                    scripts_written=scripts_written,
                    command_results=cmd_records,
                    diagnostics=[],
                    healing_action="",
                    succeeded=True,
                    duration_ms=round((time.time() - t_iter) * 1000, 1),
                ))
                overall_success = True
                break

            attempt_rec = AttemptRecord(
                attempt_number=iteration,
                plan_summary=plan.summary,
                scripts_written=scripts_written,
                command_results=cmd_records,
                diagnostics=diagnostics,
                succeeded=False,
                duration_ms=round((time.time() - t_iter) * 1000, 1),
            )

            if iteration < req.max_iterations:
                plan, heal_desc = await self._heal_plan(req, resolved_os, plan, attempt_rec)
                attempt_rec.healing_action = heal_desc
            attempts.append(attempt_rec)

        result = AutonomousSolveResult(
            job_id=job_id,
            goal=req.goal,
            resolved_os=resolved_os,
            target=target_label,
            success=overall_success,
            iterations_used=len(attempts),
            workspace_dir=str(workspace),
            attempts=attempts,
            final_output=final_output,
            summary=(
                f"Obiettivo completato autonomamente in {len(attempts)} iterazione/i su {target_label}."
                if overall_success
                else f"Obiettivo non raggiunto dopo {len(attempts)} iterazione/i su {target_label}."
            ),
        )
        self._jobs[job_id] = result
        return result

    async def _run_plan_steps(
        self,
        req: AutonomousSolveRequest,
        resolved_os: TargetOS,
        workspace: Path,
        plan: ExecutionPlan,
    ) -> Tuple[List[CommandExecutionRecord], List[DiagnosticFinding], bool]:
        cmd_records: List[CommandExecutionRecord] = []
        diagnostics: List[DiagnosticFinding] = []
        steps_to_run = list(plan.commands)
        if plan.verification_command:
            steps_to_run.append(CommandStep(
                step_id="verify_goal",
                description="Verifica finale dell'obiettivo",
                command=plan.verification_command,
            ))

        for step in steps_to_run:
            t_cmd = time.time()
            try:
                validate_command_safety(step.command)
            except SafetyViolationError as exc:
                cmd_records.append(CommandExecutionRecord(
                    step_id=step.step_id,
                    command=step.command,
                    exit_code=-2,
                    stdout="",
                    stderr=str(exc),
                    passed=False,
                    duration_ms=0.0,
                ))
                diagnostics.append(DiagnosticFinding(
                    category="safety_violation",
                    root_cause=str(exc),
                    suggested_fix_strategy="Sostituire il comando con una variante sicura.",
                ))
                return cmd_records, diagnostics, False

            exit_code, stdout, stderr = await self._execute_command(
                req=req,
                resolved_os=resolved_os,
                workspace=workspace,
                command=step.command,
                timeout=step.timeout_seconds,
            )
            passed = exit_code == step.expected_exit_code
            if passed and step.verify_stdout_contains and step.verify_stdout_contains not in stdout:
                passed = False
                stderr = (stderr + f"\nVerifica fallita: output atteso '{step.verify_stdout_contains}' non trovato.").strip()

            cmd_records.append(CommandExecutionRecord(
                step_id=step.step_id,
                command=step.command,
                exit_code=exit_code,
                stdout=stdout[-4000:],
                stderr=stderr[-4000:],
                passed=passed,
                duration_ms=round((time.time() - t_cmd) * 1000, 1),
            ))
            if not passed:
                diagnostics.extend(log_diagnostic_engine.analyze(step.command, exit_code, stdout, stderr))
                return cmd_records, diagnostics, False

        return cmd_records, diagnostics, True

    async def _resolve_target_os(self, req: AutonomousSolveRequest) -> TargetOS:
        if req.target_os != TargetOS.AUTO:
            return req.target_os
        if req.target_host:
            probe = await debian_provisioner.probe(
                DebianProbeRequest(
                    user_id=req.user_id,
                    host=req.target_host,
                    port=req.target_port,
                    username=req.target_user,
                    ssh_vault_entry_id=req.ssh_vault_entry_id,
                )
            )
            remote_info = str(probe.detected_info.get("remote_system", "")).lower()
            if "darwin" in remote_info:
                return TargetOS.MACOS
            if "windows" in remote_info or "mingw" in remote_info:
                return TargetOS.WINDOWS
            return TargetOS.LINUX
        return detect_local_os()

    def _materialize_scripts(self, workspace: Path, scripts: List[ScriptArtifact]) -> List[str]:
        written: List[str] = []
        for script in scripts:
            target_path = safe_script_path(workspace, script.filename)
            target_path.write_text(script.content, encoding="utf-8")
            if script.executable and os.name != "nt":
                try:
                    os.chmod(target_path, 0o755)
                except OSError:
                    pass
            written.append(script.filename)
        return written

    async def _execute_command(
        self,
        req: AutonomousSolveRequest,
        resolved_os: TargetOS,
        workspace: Path,
        command: str,
        timeout: float,
    ) -> Tuple[int, str, str]:
        if req.target_host:
            host, port, username, password, key_path, _ = debian_provisioner._resolve_credentials(
                DebianProbeRequest(
                    user_id=req.user_id,
                    host=req.target_host,
                    port=req.target_port,
                    username=req.target_user,
                    ssh_vault_entry_id=req.ssh_vault_entry_id,
                )
            )
            ok, _, out, err = await debian_provisioner._run_ssh_with_fallback(
                host, port, username, password, key_path, command, timeout=timeout
            )
            return (0 if ok else 1), out, err

        if resolved_os == TargetOS.WINDOWS and os.name == "nt":
            shell_cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            shell_cmd = ["bash", "-lc", command]

        proc = await asyncio.create_subprocess_exec(
            *shell_cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode or 0,
                out_b.decode("utf-8", errors="replace"),
                err_b.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", f"Command timeout after {timeout}s"

    async def _synthesize_initial_plan(self, req: AutonomousSolveRequest, resolved_os: TargetOS) -> ExecutionPlan:
        if self._planner_fn is not None:
            return await self._planner_fn(req, resolved_os)
        return await synthesize_default_plan(req, resolved_os)

    async def _heal_plan(
        self,
        req: AutonomousSolveRequest,
        resolved_os: TargetOS,
        current_plan: ExecutionPlan,
        failed_attempt: AttemptRecord,
    ) -> Tuple[ExecutionPlan, str]:
        if self._healer_fn is not None:
            return await self._healer_fn(req, resolved_os, current_plan, failed_attempt)
        return await heal_plan_default(req, resolved_os, current_plan, failed_attempt)


universal_autonomous_solver = UniversalAutonomousSolver()
