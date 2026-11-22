import json
import os
import re
import shlex
import sys
from typing import Optional, Tuple

import httpx

from server.features.autonomous_solver.models import (
    AttemptRecord,
    AutonomousSolveRequest,
    CommandStep,
    ExecutionPlan,
    ScriptArtifact,
    TargetOS,
)


def extract_json_block(text: str) -> Optional[dict]:
    cleaned = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if m:
        cleaned = m.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except Exception:
        return None


async def call_llm_for_plan(system_prompt: str, user_prompt: str) -> Optional[ExecutionPlan]:
    model = os.environ.get("NUXIVA_LLM_MODEL") or ""
    ollama_url = os.environ.get("NUXIVA_OLLAMA_URL") or "http://127.0.0.1:11434"
    if not model:
        return None
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(
                f"{ollama_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            if resp.status_code != 200:
                return None
            content = resp.json().get("message", {}).get("content", "")
            parsed = extract_json_block(content)
            if not parsed:
                return None
            return ExecutionPlan(**parsed)
    except Exception:
        return None


async def synthesize_default_plan(req: AutonomousSolveRequest, resolved_os: TargetOS) -> ExecutionPlan:
    llm_plan = await call_llm_for_plan(
        system_prompt=(
            "Sei l'architetto autonomo cross-OS di Nuxiva. Rispondi SOLO con un JSON valido che segue questo schema:\n"
            '{"summary":"...","scripts":[{"filename":"step1.py","language":"python","content":"...","purpose":"..."}],'
            '"commands":[{"step_id":"run_1","description":"...","command":"python3 step1.py"}],'
            '"verification_command":"..."}\n'
            f"Sistema operativo target: {resolved_os.value}. Preferisci Python standard cross-OS e comandi sicuri."
        ),
        user_prompt=f"Obiettivo da risolvere autonomamente: {req.goal}",
    )
    if llm_plan is not None:
        return llm_plan

    py_bin = shlex.quote(sys.executable)
    return ExecutionPlan(
        summary=f"Piano diagnostico cross-OS di fallback per {resolved_os.value}",
        target_os=resolved_os,
        scripts=[
            ScriptArtifact(
                filename="diagnose_env.py",
                language="python",
                content=(
                    "import platform, sys, json\n"
                    "print(json.dumps({'os': platform.system(), 'release': platform.release(), "
                    "'python': sys.version.split()[0], 'goal': " + repr(req.goal) + "}))\n"
                ),
                purpose="Verifica ambiente target cross-OS",
            )
        ],
        commands=[
            CommandStep(
                step_id="env_probe",
                description="Ispezione ambiente target",
                command=f"{py_bin} diagnose_env.py",
            )
        ],
    )


def deterministic_heal(
    plan: ExecutionPlan,
    failed_attempt: AttemptRecord,
) -> Tuple[Optional[ExecutionPlan], str]:
    py_bin = shlex.quote(sys.executable)
    new_plan = plan.model_copy(deep=True)

    for diag in failed_attempt.diagnostics:
        if diag.category == "missing_binary" and diag.extracted_symbol in ("python", "python3", "py"):
            replaced = False
            for step in new_plan.commands:
                updated = re.sub(r"\b(python3|python|py)\b", py_bin, step.command)
                if updated != step.command:
                    step.command = updated
                    replaced = True
            if replaced:
                return new_plan, f"Auto-fix cross-OS: sostituito '{diag.extracted_symbol}' con interprete attivo ({py_bin})."

        if diag.category == "permission_denied":
            for step in new_plan.commands:
                if step.command.strip().startswith("./"):
                    script_name = step.command.strip().split()[0][2:]
                    step.command = f"chmod +x {shlex.quote(script_name)} && {step.command}"
                    return new_plan, f"Auto-fix permessi: aggiunto chmod +x su '{script_name}'."

        if diag.category == "missing_python_module" and diag.extracted_symbol:
            pkg = diag.extracted_symbol
            if re.match(r"^[a-zA-Z0-9_\-]+$", pkg):
                install_step = CommandStep(
                    step_id=f"autofix_pip_{pkg}",
                    description=f"Installazione automatica modulo mancante {pkg}",
                    command=f"{py_bin} -m pip install -q {shlex.quote(pkg)}",
                    timeout_seconds=120.0,
                )
                new_plan.commands.insert(0, install_step)
                return new_plan, f"Auto-fix dipendenza Python: installazione automatica di '{pkg}'."

    return None, ""


async def heal_plan_default(
    req: AutonomousSolveRequest,
    resolved_os: TargetOS,
    current_plan: ExecutionPlan,
    failed_attempt: AttemptRecord,
) -> Tuple[ExecutionPlan, str]:
    det_plan, det_msg = deterministic_heal(current_plan, failed_attempt)
    if det_plan is not None:
        return det_plan, det_msg

    diag_text = "\n".join(
        f"- [{d.category}] {d.root_cause} -> {d.suggested_fix_strategy}"
        for d in failed_attempt.diagnostics
    )
    last_cmd = failed_attempt.command_results[-1] if failed_attempt.command_results else None
    err_context = (
        f"Comando fallito: {last_cmd.command}\nExit: {last_cmd.exit_code}\nSTDERR:\n{last_cmd.stderr}\nSTDOUT:\n{last_cmd.stdout}"
        if last_cmd else "Nessun output comando."
    )
    healed = await call_llm_for_plan(
        system_prompt=(
            "Sei il motore di Self-Healing autonomo di Nuxiva. Analizza l'errore nei log e restituisci "
            "SOLO un JSON ExecutionPlan corretto con script aggiornati e comandi funzionanti."
        ),
        user_prompt=(
            f"Obiettivo: {req.goal}\nOS: {resolved_os.value}\n"
            f"Piano precedente: {current_plan.model_dump_json()}\n"
            f"Diagnosi:\n{diag_text}\n{err_context}"
        ),
    )
    if healed is not None:
        return healed, "Piano riscritto autonomamente via LLM dopo analisi log."

    return current_plan, "Nessuna riparazione automatica disponibile; riprovo con il piano corrente."
