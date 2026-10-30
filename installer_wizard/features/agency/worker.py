import time

from features.agency import prompts, workspace
from features.agency.text import estimate_tokens
from features.brain import llm

WORK_TOKENS = 3500
INPUT_CHARS = 2500


def task_view(raw: dict) -> dict:
    acceptance = [c.get("text", "") if isinstance(c, dict) else str(c) for c in raw.get("acceptance", [])]
    return {"id": raw.get("id", ""), "title": raw.get("title", ""), "role": raw.get("role", ""),
            "depends_on": list(raw.get("depends_on", [])), "acceptance": [a for a in acceptance if a],
            "feedback": raw.get("feedback") or ""}


def deliverable_path(context: dict, task_id: str) -> str:
    return f"{context['work_dir']}/{task_id}.md"


def inputs(context: dict, task: dict) -> str:
    parts = []
    for dep in task["depends_on"]:
        body = workspace.read(context["folder"], deliverable_path(context, dep), INPUT_CHARS)
        if body:
            parts.append(f"### {dep}\n{body}")
    return "\n\n".join(parts)


async def execute(context: dict, task: dict) -> tuple[str, int, int]:
    started = time.monotonic()
    role = next((r for r in context["blueprint"]["roles"] if r["id"] == task["role"]), {})
    prompt = prompts.work(context["goal"], context["blueprint"].get("architecture", ""), role.get("mission", ""),
                          task, inputs(context, task), context["language_name"])
    text = await llm.generate(prompt, max_tokens=WORK_TOKENS, temperature=0.2, kind="deep",
                              system=prompts.WORKER, component="agency_worker")
    body = str(text or "").strip()
    if body:
        workspace.write(context["folder"], deliverable_path(context, task["id"]), body + "\n")
    return body, estimate_tokens(prompt, body), max(1, int(time.monotonic() - started))
