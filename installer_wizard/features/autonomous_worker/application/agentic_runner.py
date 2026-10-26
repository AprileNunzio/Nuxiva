import json
import logging
from typing import Any

from features.agent import registry
from features.autonomous_worker.application.tool_catalog import tool_catalog
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.domain.models import Mission, Task

log = logging.getLogger("nuxiva.autonomous_worker.agentic_runner")
MAX_AGENTIC_STEPS = 12


class AgenticSpecialistRunner:
    def __init__(self) -> None:
        self.max_steps = MAX_AGENTIC_STEPS

    def get_available_tools_description(self, task: Task) -> str:
        relevant_tools = tool_catalog.get_relevant_tools_for_task(task, limit=80)
        tools_list = []
        for item in relevant_tools:
            name = item["name"]
            args_dict = item.get("args") or {}
            args_desc = ", ".join(f"{k}: {v}" for k, v in args_dict.items())
            desc = str(item.get("description", ""))[:120]
            tools_list.append(f"- {name}({args_desc}): {desc}")
        return "\n".join(tools_list)

    async def execute_task_with_tools(self, mission: Mission, task: Task, base_prompt: str) -> dict[str, Any]:
        tools_desc = self.get_available_tools_description(task)
        history = [
            f"STRUMENTI REALI DISPONIBILI SUL SERVER:\n{tools_desc}\n",
            "ISTRUZIONI: Se hai bisogno di strumenti per leggere, scrivere o testare, rispondi con:",
            '{"tool": "nome_strumento", "args": {...}}',
            "Quando hai completato tutto il lavoro e verificato i criteri, rispondi con:",
            '{"result": "sintesi esecutiva", "artifacts": [{"path": "...", "content": "..."}], "collab_note": "..."}',
        ]

        steps = 0
        final_result: dict[str, Any] = {"result": "", "artifacts": []}

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
                        "Sei uno specialista d'élite con strumenti reali. Esegui azioni concrete per soddisfare i criteri. "
                        "Non tirare a indovinare: usa read_file, write_file o i tool idonei."
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

            if "tool" in res and res.get("tool") in registry.TOOLS:
                tool_name = str(res["tool"])
                tool_args = res.get("args", {}) if isinstance(res.get("args"), dict) else {}
                tool_meta = registry.TOOLS[tool_name]
                try:
                    fn = tool_meta["fn"]
                    import asyncio
                    if asyncio.iscoroutinefunction(fn):
                        out = await fn(**tool_args)
                    else:
                        out = fn(**tool_args)
                    tool_out_str = str(out)[:1500]
                except Exception as exc:
                    tool_out_str = f"ERRORE STRUMENTO {tool_name}: {exc}"

                history.append(f"AZIONE: {tool_name}({json.dumps(tool_args)}) -> ESITO: {tool_out_str}")
            elif "result" in res:
                final_result = res
                break
            else:
                final_result = res
                break

        return final_result


agentic_runner = AgenticSpecialistRunner()
