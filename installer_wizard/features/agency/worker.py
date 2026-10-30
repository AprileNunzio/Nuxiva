from features.agency import agent, tools, workspace
from features.agency.text import clean

INPUT_CHARS = 2500
EVIDENCE_FILES = 4
EVIDENCE_CHARS = 1500


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


def report(outcome: agent.Outcome, ctx: tools.Context) -> str:
    lines = [outcome.summary or "(no summary)", ""]
    lines += [f"- `{path}`" for path in ctx.written]
    lines += [f"- tool `x_{name}`" for name in ctx.forged]
    for check in ctx.checks:
        lines += ["", f"`{check['check']} {check['entry']}`".strip() + f" → exit {check['exit_code']}",
                  "```", check["output"][-800:], "```"]
    return "\n".join(lines).strip() + "\n"


def evidence(context: dict, body: str, ctx: tools.Context) -> str:
    parts = [body]
    for path in ctx.written[:EVIDENCE_FILES]:
        excerpt = workspace.read(context["folder"], path, EVIDENCE_CHARS)
        parts.append(f"--- {path} ---\n{excerpt}")
    return "\n".join(parts)


async def execute(context: dict, project_id: str, task: dict) -> tuple[str, str, int]:
    role = next((r for r in context["blueprint"]["roles"] if r["id"] == task["role"]), {})
    brief = {"goal": context["goal"], "architecture": context["blueprint"].get("architecture", ""),
             "mission": clean(role.get("mission"), 400), "inputs": inputs(context, task),
             "language_name": context["language_name"]}
    ctx = tools.Context(project_id, context["folder"], task=task.get("title", ""))
    outcome = await agent.act(brief, task, ctx)
    body = report(outcome, ctx) if (outcome.summary or ctx.written) else ""
    if body:
        workspace.write(context["folder"], deliverable_path(context, task["id"]), body)
    return body, evidence(context, body, ctx) if body else "", outcome.tokens + ctx.tokens
