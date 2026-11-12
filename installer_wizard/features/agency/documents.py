from features.agency.blueprint import Blueprint
from features.agency.critic import Reasoning
from features.agency.words import word


def plan(blueprint: Blueprint, goal: str, lang: str) -> str:
    w = lambda key: word(lang, "files", key)
    lines = [f"# {blueprint.title}", "", f"## {w('goal')}", "", goal, ""]
    if blueprint.summary:
        lines += [blueprint.summary, ""]
    if blueprint.architecture:
        lines += [f"## {w('architecture')}", "", blueprint.architecture, ""]
    lines += [f"## {w('roles')}", ""]
    lines += [f"- **{r.id}**" + (f": {r.mission}" if r.mission else "") for r in blueprint.roles]
    lines += ["", f"## {w('tasks')}", ""]
    for task in blueprint.tasks:
        deps = f" ({w('depends')}: {', '.join(task.depends_on)})" if task.depends_on else ""
        lines.append(f"1. `{task.id}` **{task.title}** [{task.role}]{deps}")
        lines += [f"    - {c}" for c in task.acceptance]
    return "\n".join(lines) + "\n"


def reasoning(data: Reasoning, lang: str) -> str:
    w = lambda key: word(lang, "files", key)
    lines = [f"# {w('reasoning')}", ""]
    for item in data.exchanges:
        lines += [f"**{w('question')}:** {item.question}", "", f"**{w('answer')}:** {item.answer}", ""]
    if data.issues:
        lines += [f"## {w('issues')}", ""] + [f"- {issue}" for issue in data.issues]
    return "\n".join(lines) + "\n"
