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

AGENT = (
    "You are a senior specialist agent of the agency working inside the project folder with tools. Work like a "
    "careful engineer: look at what exists, write complete files (never placeholders), run the available checks when "
    "they apply, fix what fails, and stop when the acceptance criteria are met. Each reply is exactly one JSON object: "
    "either {\"thought\": ..., \"tool\": name, \"args\": {...}} to use a tool, or {\"thought\": ..., \"final\": "
    "\"Markdown summary of what you delivered, files and check results\"} when done. Never claim a check passed unless "
    "you ran it."
)

FORGE = (
    "You are the Toolsmith of the agency. You write one small, pure, deterministic Python tool that other agents will "
    "reuse. It receives a JSON object and returns JSON-serialisable data. No files, network, processes, printing, "
    "introspection or dunder names; standard library only from the allowed modules. Every tool ships with tests that "
    "prove it works. Answer only with JSON."
)

FORGE_SHAPE = {
    "name": "lowercase_identifier",
    "description": "one sentence on what the tool does",
    "args": {"argument": "meaning and type"},
    "code": "import math\n\ndef run(args):\n    ...\n    return result",
    "tests": [{"args": {"argument": "value"}, "expect": "exact expected result"}],
}

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


def review(task: dict, delivered: str, language_name: str) -> str:
    criteria = "\n".join(f"- {c}" for c in task.get("acceptance", []))
    return (f"Task: {task.get('title')}\nAcceptance criteria:\n{criteria or '- complete and correct'}\n\n"
            f"Delivered evidence:\n{delivered[:9000]}\n\n{language_rule(language_name)}\n"
            f"Return JSON shaped like: {json.dumps(REVIEW_SHAPE, ensure_ascii=False)}")


def act(brief: dict, task: dict, manifest: list[dict], history: str, step: int, max_steps: int) -> str:
    criteria = "\n".join(f"- {c}" for c in task.get("acceptance", []))
    feedback = task.get("feedback") or ""
    return (f"Project goal:\n{brief['goal']}\n\nArchitecture:\n{brief['architecture'][:3000]}\n\n"
            f"Your role: {task.get('role')} - {brief['mission']}\nTask: {task.get('title')}\n"
            f"Acceptance criteria:\n{criteria or '- complete and correct'}\n"
            + (f"Rework requested by the Critic:\n{feedback}\n" if feedback else "")
            + (f"Results of the tasks you depend on:\n{brief['inputs'][:5000]}\n" if brief.get("inputs") else "")
            + f"\nTools:\n{json.dumps(manifest, ensure_ascii=False)}\n"
            + (f"\nWhat you did so far:\n{history}\n" if history else "")
            + f"\nStep {step} of {max_steps}. {language_rule(brief['language_name'])}")


def forge(need: dict, allowed: list[str], failure: str) -> str:
    return (f"An agent needs a new tool.\nSuggested name: {need['name']}\nPurpose: {need['purpose']}\n"
            f"Example use: {need['example']}\n\nAllowed modules: {', '.join(allowed)}.\n"
            "Write def run(args) at top level. Give 2 to 6 tests with exact expected results, edge cases included.\n"
            + (f"Your previous attempt failed: {failure}\nFix it.\n" if failure else "")
            + f"Return JSON shaped like: {json.dumps(FORGE_SHAPE, ensure_ascii=False)}")
