import asyncio
import os
from pathlib import Path
import shutil
import sys
from typing import Any

from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.sandbox_validator import sandbox_validator
from features.autonomous_worker.domain.exceptions import MissionValidationError
from features.autonomous_worker.domain.models import Mission, Task
from features.autonomous_worker.domain.sanitizer import resolve_safe_path
from features.autonomous_worker.infrastructure.artifact_vault import vault

SANDBOX_TIMEOUT = 15
OUTPUT_CAP = 6000

WORKSPACE_TOOLS_SPEC = [
    "- workspace_read_file(path: str, start_line: int = 1, end_line: int = 200): Legge un file del workspace della missione con numeri di riga.",
    "- workspace_search(query: str, file_pattern: str = '*'): Cerca testo o simboli in tutti i file del workspace della missione.",
    "- workspace_write_file(path: str, content: str, title: str = ''): Crea o aggiorna un file nel workspace validando sintassi e limite 500 righe.",
    "- workspace_patch_file(path: str, target_block: str, replacement_block: str): Applica una patch chirurgica atomica a un file esistente del workspace.",
    "- workspace_verify(check_type: str = 'auto', entry_path: str = ''): Esegue compilazione, test unitari reali e verifica dei contratti cross-file nel workspace.",
]


class MissionWorkspaceRuntime:
    @staticmethod
    def _sanitized_env(folder: Path) -> dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(folder),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "NODE_ENV": "test",
            "PYTHONPATH": str(folder),
        }
        for win_key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"):
            if win_key in os.environ:
                env[win_key] = os.environ[win_key]
        return env

    @classmethod
    async def _run_isolated_cmd(cls, argv: list[str], cwd: Path) -> tuple[int, str]:
        cmd = list(argv)
        if sys.platform == "linux":
            unshare_bin = shutil.which("unshare")
            if unshare_bin:
                cmd = [unshare_bin, "--net", "--", *cmd]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                env=cls._sanitized_env(cwd),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except OSError as exc:
            return 1, f"Impossibile avviare processo sandbox: {exc}"

        try:
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=SANDBOX_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return 124, f"Timeout esecuzione sandbox dopo {SANDBOX_TIMEOUT}s"

        out_text = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        return int(proc.returncode or 0), out_text[-OUTPUT_CAP:]

    @classmethod
    async def verify_workspace(
        cls,
        mission: Mission,
        check_type: str = "auto",
        entry_path: str = "",
    ) -> dict[str, Any]:
        mdir = vault.mission_dir(mission.id)
        checks_run: list[str] = []
        outputs: list[str] = []
        overall_passed = True
        last_code = 0

        for art in mission.artifacts:
            try:
                content = vault.read_file(mission.id, art.relative_path)
            except OSError:
                continue
            valid, err_msg = sandbox_validator.validate_code(art.relative_path, content)
            if not valid:
                overall_passed = False
                last_code = 2
                outputs.append(f"[STATIC_VALIDATION_FAIL] {art.relative_path}: {err_msg}")
        checks_run.append("static_ast_and_500_lines")

        _, contract_warnings = code_intel.analyze_dependencies(mission)
        checks_run.append("cross_file_contracts")
        if contract_warnings:
            for w in contract_warnings:
                outputs.append(f"[CONTRACT_WARNING] {w}")

        py_files = [a.relative_path for a in mission.artifacts if a.relative_path.endswith(".py")]
        py_tests = [
            p for p in py_files
            if Path(p).name.startswith("test_") or Path(p).name.endswith("_test.py")
        ]

        if check_type in ("auto", "python_compile") and py_files and sys.executable:
            code, out = await cls._run_isolated_cmd(
                [sys.executable, "-B", "-m", "compileall", "-q", "."],
                mdir,
            )
            checks_run.append("python_compile")
            if code != 0:
                overall_passed = False
                last_code = code
                outputs.append(f"[PYTHON_COMPILE_FAIL]\n{out}")

        if check_type in ("auto", "python_tests") and py_tests and sys.executable:
            code, out = await cls._run_isolated_cmd(
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-t", ".", "-p", "*test*.py"],
                mdir,
            )
            checks_run.append("python_tests")
            outputs.append(f"[PYTHON_UNITTESTS (exit={code})]\n{out.strip()}")
            if code != 0:
                overall_passed = False
                last_code = code

        if check_type == "python_run" and entry_path and sys.executable:
            target = resolve_safe_path(mdir, entry_path)
            if target.is_file() and target.suffix == ".py":
                rel = target.relative_to(mdir).as_posix()
                code, out = await cls._run_isolated_cmd([sys.executable, "-B", rel], mdir)
                checks_run.append(f"python_run:{rel}")
                outputs.append(f"[PYTHON_RUN {rel} (exit={code})]\n{out.strip()}")
                if code != 0:
                    overall_passed = False
                    last_code = code

        return {
            "passed": overall_passed,
            "exit_code": last_code,
            "checks_run": checks_run,
            "contract_warnings": contract_warnings,
            "output": "\n".join(outputs).strip() or "Tutte le verifiche statiche, contrattuali e runtime superate.",
        }

    @classmethod
    def is_workspace_tool(cls, tool_name: str) -> bool:
        return tool_name in {
            "workspace_read_file",
            "workspace_search",
            "workspace_write_file",
            "workspace_patch_file",
            "workspace_verify",
        }

    @classmethod
    async def execute_workspace_tool(
        cls,
        mission: Mission,
        task: Task,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> str:
        role = task.specialist_role or "Specialista"
        sender = task.specialist_id or "worker"

        if tool_name == "workspace_read_file":
            rel_path = str(tool_args.get("path", "")).strip()
            start_line = int(tool_args.get("start_line", 1))
            end_line = int(tool_args.get("end_line", 200))
            if not rel_path:
                return "ERRORE: parametro 'path' obbligatorio"
            return vault.read_file_lines(mission.id, rel_path, start_line, end_line)

        if tool_name == "workspace_search":
            query = str(tool_args.get("query", "")).strip()
            pattern = str(tool_args.get("file_pattern", "*")).strip() or "*"
            matches = vault.search_workspace(mission.id, query, pattern)
            if not matches:
                return f"Nessuna occorrenza per '{query}' nel workspace."
            return "\n".join(f"{m['path']}:{m['line']}: {m['snippet']}" for m in matches)

        if tool_name == "workspace_write_file":
            rel_path = str(tool_args.get("path", "")).strip()
            content = str(tool_args.get("content", ""))
            title = str(tool_args.get("title", ""))
            if not rel_path or not content:
                return "ERRORE: parametri 'path' e 'content' obbligatori"
            valid, err_msg = sandbox_validator.validate_code(rel_path, content)
            if not valid:
                return f"VALIDAZIONE FALLITA: {err_msg}"
            art = vault.store_file(
                mission=mission,
                relative_path=rel_path,
                content=content,
                generated_by=role,
                title=title,
            )
            collab_bus.post(
                mission=mission,
                sender_id=sender,
                sender_role=role,
                content=f"[Tool Write] Scritto «{art.relative_path}» (v{art.version}, {art.line_count}L, {len(art.symbols)} simboli).",
                kind="artifact",
                artifact_ref=art.relative_path,
            )
            return f"OK: salvato {art.relative_path} (v{art.version}, checksum={art.checksum[:10]}, {art.line_count} righe)"

        if tool_name == "workspace_patch_file":
            rel_path = str(tool_args.get("path", "")).strip()
            target_block = str(tool_args.get("target_block", ""))
            replacement_block = str(tool_args.get("replacement_block", ""))
            expected_checksum = str(tool_args.get("expected_checksum", ""))
            if not rel_path or not target_block:
                return "ERRORE: parametri 'path' e 'target_block' obbligatori"
            try:
                art = vault.apply_atomic_patch(
                    mission=mission,
                    relative_path=rel_path,
                    target_block=target_block,
                    replacement_block=replacement_block,
                    generated_by=role,
                    expected_checksum=expected_checksum,
                )
            except (FileNotFoundError, MissionValidationError) as exc:
                return f"PATCH FALLITA: {exc}"
            collab_bus.post(
                mission=mission,
                sender_id=sender,
                sender_role=role,
                content=f"[Tool Patch] Aggiornato «{art.relative_path}» (v{art.version}, {art.line_count}L).",
                kind="artifact",
                artifact_ref=art.relative_path,
            )
            return f"OK: patch applicata a {art.relative_path} (v{art.version}, checksum={art.checksum[:10]})"

        if tool_name == "workspace_verify":
            check_type = str(tool_args.get("check_type", "auto"))
            entry_path = str(tool_args.get("entry_path", ""))
            report = await cls.verify_workspace(mission, check_type=check_type, entry_path=entry_path)
            status_label = "SUPERATA" if report["passed"] else "FALLITA"
            return (
                f"VERIFICA WORKSPACE {status_label} (exit={report['exit_code']})\n"
                f"Controlli: {', '.join(report['checks_run'])}\n"
                f"Dettagli:\n{report['output']}"
            )

        return f"Strumento workspace sconosciuto: {tool_name}"


workspace_runtime = MissionWorkspaceRuntime()
