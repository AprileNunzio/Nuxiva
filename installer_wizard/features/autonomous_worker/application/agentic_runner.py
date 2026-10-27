import asyncio
import json
import logging
import time
from typing import Any

from features.agent import registry
from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.tool_catalog import tool_catalog
from features.autonomous_worker.application.workspace_runtime import (
    WORKSPACE_TOOLS_SPEC,
    workspace_runtime,
)
from features.autonomous_worker.domain.models import Mission, MissionQuestion, ReasoningStep, Task
from features.autonomous_worker.domain.sanitizer import sanitize_text
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager

log = logging.getLogger("nuxiva.autonomous_worker.agentic_runner")
MAX_AGENTIC_STEPS = 12


class AgenticSpecialistRunner:
    def __init__(self) -> None:
        self.max_steps = MAX_AGENTIC_STEPS

    def get_available_tools_description(self, task: Task) -> str:
        relevant_tools = tool_catalog.get_relevant_tools_for_task(task, limit=65)
        tools_list = list(WORKSPACE_TOOLS_SPEC)
        for item in relevant_tools:
            name = item["name"]
            args_dict = item.get("args") or {}
            args_desc = ", ".join(f"{k}: {v}" for k, v in args_dict.items())
            desc = str(item.get("description", ""))[:120]
            tools_list.append(f"- {name}({args_desc}): {desc}")
        return "\n".join(tools_list)

    async def execute_task_with_tools(self, mission: Mission, task: Task, base_prompt: str) -> dict[str, Any]:
        tools_desc = self.get_available_tools_description(task)
        focus_query = f"{task.title} {task.description}"
        repo_map = code_intel.build_repo_map(mission, focus_text=focus_query)
        history = [
            f"{repo_map}\n",
            f"STRUMENTI WORKSPACE & SERVER DISPONIBILI:\n{tools_desc}\n",
            "ISTRUZIONI: Usa workspace_read_file, workspace_search, workspace_write_file, workspace_patch_file o workspace_verify per ispezionare, modificare e testare il codice prima di chiudere il task:",
            '{"thought": "ragionamento tecnico", "doubt": "eventuale dubbio analizzato", "tool": "nome_strumento", "args": {...}}',
            "Quando hai completato tutto il lavoro e verificato i criteri, rispondi con:",
            '{"thought": "sintesi del ragionamento", "doubts": ["dubbio 1 risolto o segnalato"], "result": "sintesi esecutiva", "artifacts": [{"path": "...", "content": "..."}], "patches": [{"path": "...", "target": "...", "replacement": "..."}], "collab_note": "..."}',
        ]

        steps = 0
        final_result: dict[str, Any] = {"result": "", "artifacts": [], "patches": []}

        while steps < self.max_steps:
            steps += 1
            full_prompt = base_prompt + "\n\nCRONOLOGIA OPERAZIONI:\n" + "\n".join(history[-8:])
            try:
                res = await runtime_manager.generate(
                    full_prompt,
                    as_json=True,
                    max_tokens=3500,
                    temperature=0.2,
                    system=(
                        "Sei uno specialista d'élite con strumenti reali. Applica Clean Architecture, Zero-Trust, "
                        "codice puro senza commenti, file sotto le 500 righe e struttura feature-based. "
                        "Rispetta i contratti cross-file della Repository Map ed esponi sempre 'thought' ed eventuali 'doubt'."
                    ),
                    component="autonomous_worker",
                    agent_id=task.specialist_id,
                    agent_role=task.specialist_role,
                )
            except Exception as exc:
                final_result["result"] = f"Errore inferenza: {exc}"
                break

            if not isinstance(res, dict):
                final_result["result"] = str(res)
                break

            thought_text = sanitize_text(res.get("thought") or "", 600)
            doubt_text = sanitize_text(res.get("doubt") or "", 400)
            if doubt_text and doubt_text not in task.doubts:
                task.doubts.append(doubt_text)
                collab_bus.post(
                    mission=mission,
                    sender_id=task.specialist_id or "worker",
                    sender_role=task.specialist_role or "Specialista",
                    content=f"[DUBBIO TECNICO - {task.title}]: {doubt_text}",
                    kind="doubt",
                )

            req_tool = str(res.get("tool") or "").strip()
            if req_tool and (workspace_runtime.is_workspace_tool(req_tool) or req_tool in registry.TOOLS):
                tool_args = res.get("args", {}) if isinstance(res.get("args"), dict) else {}
                try:
                    if workspace_runtime.is_workspace_tool(req_tool):
                        tool_out_str = await workspace_runtime.execute_workspace_tool(
                            mission=mission,
                            task=task,
                            tool_name=req_tool,
                            tool_args=tool_args,
                        )
                    else:
                        tool_meta = registry.TOOLS[req_tool]
                        fn = tool_meta["fn"]
                        if asyncio.iscoroutinefunction(fn):
                            out = await fn(**tool_args)
                        else:
                            out = fn(**tool_args)
                        tool_out_str = str(out)[:1500]
                except Exception as exc:
                    tool_out_str = f"ERRORE STRUMENTO {req_tool}: {exc}"

                step_record = ReasoningStep(
                    step_index=len(task.reasoning_steps) + 1,
                    thought=thought_text or f"Esecuzione strumento {req_tool}",
                    doubt=doubt_text,
                    tool_name=req_tool,
                    tool_args=tool_args,
                    tool_output=tool_out_str[:600],
                    timestamp=time.time(),
                )
                task.reasoning_steps.append(step_record)
                if thought_text:
                    collab_bus.post(
                        mission=mission,
                        sender_id=task.specialist_id or "worker",
                        sender_role=task.specialist_role or "Specialista",
                        content=f"[RAGIONAMENTO] {thought_text} -> Tool: {req_tool}",
                        kind="thought",
                    )

                history.append(f"AZIONE: {req_tool}({json.dumps(tool_args)}) -> ESITO: {tool_out_str}")
            else:
                if thought_text:
                    task.reasoning_steps.append(
                        ReasoningStep(
                            step_index=len(task.reasoning_steps) + 1,
                            thought=thought_text,
                            doubt=doubt_text,
                            timestamp=time.time(),
                        )
                    )
                    collab_bus.post(
                        mission=mission,
                        sender_id=task.specialist_id or "worker",
                        sender_role=task.specialist_role or "Specialista",
                        content=f"[RAGIONAMENTO FINALE - {task.title}]: {thought_text}",
                        kind="thought",
                    )
                for raw_d in res.get("doubts", []) if isinstance(res.get("doubts"), list) else []:
                    clean_d = sanitize_text(str(raw_d), 400)
                    if clean_d and clean_d not in task.doubts:
                        task.doubts.append(clean_d)
                        collab_bus.post(
                            mission=mission,
                            sender_id=task.specialist_id or "worker",
                            sender_role=task.specialist_role or "Specialista",
                            content=f"[DUBBIO EMERSO - {task.title}]: {clean_d}",
                            kind="doubt",
                        )
                raw_q = res.get("question")
                if isinstance(raw_q, dict) and raw_q.get("question"):
                    q_obj = MissionQuestion(
                        id=f"q_{len(mission.questions) + 1}_{int(time.time()) % 1000}",
                        question=sanitize_text(raw_q.get("question"), 300),
                        options=[
                            sanitize_text(o, 120)
                            for o in raw_q.get("options", [])
                            if isinstance(o, str)
                        ],
                        rationale=sanitize_text(raw_q.get("rationale", ""), 240),
                        asked_by=task.specialist_role or "Specialista",
                    )
                    mission.questions.append(q_obj)

                final_result = res
                break

        return final_result


agentic_runner = AgenticSpecialistRunner()
