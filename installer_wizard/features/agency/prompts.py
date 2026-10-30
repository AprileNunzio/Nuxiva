import json

DIRECTOR = (
    "You are the Director of a software and project agency. Think before you plan: find the best solution, "
    "the architecture that reaches it and the specialists it needs. Break the work into small, verifiable tasks "
    "forming a dependency graph; a task may only depend on tasks listed before it. Every task has concrete "
    "acceptance criteria that a reviewer can check from the delivered evidence. Prefer modern, secure, maintainable "
    "choices. Never invent facts about the user. Answer only with JSON."
)

CRITIC = (
    "You are the Critic of the agency. You challenge the plan by asking yourself the hard questions a senior "
    "engineer, a security auditor and the end user would ask, and you answer each one honestly. You report real "
    "gaps only and propose the missing tasks needed to close them. Answer only with JSON."
)

REVIEWER = (
    "You are the Critic reviewing one delivered task. Judge only the evidence received, never promises. Approve only "
    "when every acceptance criterion is met; otherwise ask for precise rework. Answer only with JSON."
)

WORKER = (
    "You are a senior specialist of the agency executing one task of a larger project. Deliver the complete work "
    "product, not a description of it: real content, real code or real specifications, ready to use. Respect the "
    "architecture and the acceptance criteria. Follow modern security practices."
)

PLAN_SHAPE = {
    "title": "short project name",
    "summary": "what will be built and why this solution",
    "architecture": "components, technologies and how they interact",
    "roles": [{"id": "backend", "mission": "what this specialist owns"}],
    "tasks": [{"id": "api-catalog", "title": "what to do", "role": "backend", "depends_on": ["earlier-task-id"],
               "acceptance": ["checkable criterion"], "estimate_seconds": 900}],
}

CRITIQUE_SHAPE = {
    "questions": [{"q": "hard question", "a": "honest answer"}],
    "issues": ["real gap found"],
    "missing_tasks": [{"id": "new-id", "title": "...", "role": "existing-role-id", "depends_on": [],
                       "acceptance": ["..."], "estimate_seconds": 600}],
    "verdict": "ok or revise",
}

REVIEW_SHAPE = {"verdict": "approve or rework", "feedback": "precise instructions when rework", "checks": [{"criterion": "...", "met": True}]}


def language_rule(language_name: str) -> str:
    return f"Write every human-readable value in {language_name}. Keep ids as lowercase ascii slugs."


def plan(goal: str, language_name: str) -> str:
    return (f"Project request from the user:\n{goal}\n\n{language_rule(language_name)}\n"
            f"Return JSON shaped like: {json.dumps(PLAN_SHAPE, ensure_ascii=False)}")


def critique(goal: str, blueprint: dict, language_name: str) -> str:
    return (f"User request:\n{goal}\n\nPlan under review:\n{json.dumps(blueprint, ensure_ascii=False)[:12000]}\n\n"
            f"Ask yourself at least five hard questions and answer them. {language_rule(language_name)}\n"
            f"Return JSON shaped like: {json.dumps(CRITIQUE_SHAPE, ensure_ascii=False)}")


def work(goal: str, architecture: str, mission: str, task: dict, inputs: str, language_name: str) -> str:
    criteria = "\n".join(f"- {c}" for c in task.get("acceptance", []))
    feedback = task.get("feedback") or ""
    return (f"Project goal:\n{goal}\n\nArchitecture:\n{architecture[:3000]}\n\nYour role: {task.get('role')} - {mission}\n"
            f"Task: {task.get('title')}\nAcceptance criteria:\n{criteria or '- complete and correct'}\n"
            + (f"Rework requested by the Critic:\n{feedback}\n" if feedback else "")
            + (f"Results of the tasks you depend on:\n{inputs[:6000]}\n" if inputs else "")
            + f"\n{language_rule(language_name)} Deliver the work product in Markdown.")


def review(task: dict, delivered: str, language_name: str) -> str:
    criteria = "\n".join(f"- {c}" for c in task.get("acceptance", []))
    return (f"Task: {task.get('title')}\nAcceptance criteria:\n{criteria or '- complete and correct'}\n\n"
            f"Delivered evidence:\n{delivered[:9000]}\n\n{language_rule(language_name)}\n"
            f"Return JSON shaped like: {json.dumps(REVIEW_SHAPE, ensure_ascii=False)}")
