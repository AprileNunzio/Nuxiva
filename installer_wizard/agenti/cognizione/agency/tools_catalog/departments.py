import json

from agenti.agency.scanner.department_scanner import (
    forge_department,
    scan_departments,
)


async def _forge_department_agent(ctx, args: dict) -> str:
    domain = str(args.get("domain", "")).strip()[:40]
    if not domain:
        raise ValueError("argument 'domain' is required")
    name = str(args.get("agent_name", "")).strip()[:120]
    dept_name = str(args.get("department_name", "")).strip()[:120]
    prompt = str(args.get("system_prompt", "")).strip()[:2000]
    skills = args.get("skills") if isinstance(args.get("skills"), list) else None
    widgets = args.get("widgets") if isinstance(args.get("widgets"), list) else None
    created = forge_department(
        domain=domain,
        name=name,
        dept_name=dept_name,
        prompt=prompt,
        skills=skills,
        widgets=widgets,
    )
    return json.dumps({
        "status": "forged",
        "department_id": created["id"],
        "name": created["name"],
        "department": created["department"],
        "skills": created["skills"],
        "widgets": created["widgets"],
    }, ensure_ascii=False)


async def _list_departments(ctx, args: dict) -> str:
    deps = scan_departments()
    summary = [
        {
            "id": d["id"],
            "name": d["name"],
            "department": d["department"],
            "skills": d["skills"][:5],
            "capabilities": d["capabilities"][:5],
            "widgets": [w.get("title") for w in d["widgets"]],
        }
        for d in deps.values()
    ]
    return json.dumps({"departments": summary, "count": len(summary)}, ensure_ascii=False)


async def _ask_clarification(ctx, args: dict) -> str:
    question = str(args.get("question", "")).strip()[:1000]
    options = args.get("options", [])
    if not question:
        raise ValueError("argument 'question' is required for clarification")
    clean_options = [str(o)[:120] for o in options if isinstance(o, (str, int))]
    return json.dumps({
        "status": "awaiting_user_input",
        "dialogue_turn": "clarification_prompt",
        "question": question,
        "options": clean_options,
    }, ensure_ascii=False)


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("forge_department_agent", "Dynamically forge a brand new independent department and specialist agent with custom prompt, skills, and UI widgets.",
             {"domain": "medicine", "agent_name": "Dr. Roberto", "department_name": "Medicina Generale", "system_prompt": "Sei l'esperto medico...", "skills": ["diagnosis", "pharma"]},
             "forge", _forge_department_agent),
        Tool("list_departments", "Scan and list all available enterprise departments, what they can do, and their widgets.",
             {}, "read", _list_departments),
        Tool("ask_clarification", "Trigger an interactive question-answer clarification loop with the user for missing details.",
             {"question": "Qual è il numero da chiamare?", "options": ["+39...", "+1..."]}, "execute", _ask_clarification),
    ]
