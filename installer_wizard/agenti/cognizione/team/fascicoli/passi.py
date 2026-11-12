import hashlib
import json

MAX_ARGS = 400
MAX_RESULT = 1500
MAX_WHY = 200


def _args_text(args: dict) -> str:
    return json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)[:MAX_ARGS]


def step_sections(t: dict, tool: str, agent: str, args: dict, result: str, ok: bool, ms: int, sealed: bool) -> dict:
    if sealed:
        names = ", ".join(sorted(str(k) for k in args)) or t["step_none"]
        tool_line = t["step_tool_sealed"].format(tool=tool, names=names)
        digest = hashlib.sha256(result.encode()).hexdigest()[:12]
        result_text = t["step_result_sealed"].format(chars=len(result), digest=digest)
    else:
        tool_line = t["step_tool"].format(tool=tool, args=_args_text(args))
        result_text = result[:MAX_RESULT] or t["answer_empty"]
    why = " ".join(result.split())[:MAX_WHY]
    return {
        "goal": t["step_goal"].format(tool=tool, agent=agent),
        "tool": tool_line,
        "result": result_text,
        "check": t["check_ok"].format(ms=ms) if ok else t["check_error"].format(why=why if not sealed else t["step_none"]),
        "status": t["status_ok"] if ok else t["status_error"],
    }


def verifica_sections(t: dict, report: dict, facts: dict, judgement: dict) -> dict:
    lines = []
    for check in judgement["checks"]:
        mark = t["mark_ok"] if check["ok"] else t["mark_ko"]
        lines.append(f"- {mark} {t['v_' + check['id']]}")
    evidence = [
        t["ev_files"].format(files=", ".join(report.get("files", [])) or t["step_none"]),
        t["ev_steps"].format(total=facts["steps_total"], failed=facts["steps_failed"]),
        t["ev_outcome"].format(status=facts["outcome_status"] or t["step_none"]),
    ]
    problems = report.get("problems", [])
    if problems:
        evidence.append(t["ev_problems"].format(problems=", ".join(f"{p['at']}:{p['code']}" for p in problems[:8])))
    return {"criteria": "\n".join(lines), "evidence": "\n".join(evidence), "verdict": t["verdict_" + judgement["verdict"]]}
