from agenti.team.fascicoli import formato

BAD_STATUS = ("failed", "blocked", "cancelled", "error")


def judge(report: dict, facts: dict) -> dict:
    level = report.get("level", "")
    required = [k for k in formato.LEVELS.get(level, ()) if k != "verifica"]
    files = level in formato.LEVELS and all(
        any(formato.kind_of_name(f) == k for f in report.get("files", [])) for k in required)
    chain = bool(report.get("ok"))
    steps = facts.get("steps_failed", 0) == 0
    bad = facts.get("outcome_status", "") in BAD_STATUS
    outcome = bool(facts.get("outcome_verified")) and not bad
    answer = not facts.get("answer_empty", False)
    checks = [{"id": "chain", "ok": chain}, {"id": "files", "ok": files}, {"id": "steps", "ok": steps},
              {"id": "outcome", "ok": outcome}, {"id": "answer", "ok": answer}]
    if not chain or not steps or bad:
        verdict = "non_superata"
    elif not files or not outcome or not answer:
        verdict = "incompleta"
    else:
        verdict = "superata"
    return {"verdict": verdict, "checks": checks}
