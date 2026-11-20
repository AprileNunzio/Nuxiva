import json

from agenti.agency.solution_bank import solution_bank
from agenti.agency.tools import Context, Tool, _text


async def _solution_bank_query(ctx: Context, args: dict) -> str:
    query = _text(args, "query", 500)
    domain = _text(args, "domain", 60, required=False) or None

    match = solution_bank.find_best_solution(query, domain=domain)
    if not match:
        return json.dumps({"status": "no_match", "message": "Nessuna soluzione pregressa trovata per questa richiesta."}, ensure_ascii=False)

    entry, score = match
    return json.dumps({
        "status": "matched",
        "solution_id": entry.solution_id,
        "title": entry.title,
        "domain": entry.domain,
        "confidence_score": score,
        "quality_score": entry.quality_score,
        "usage_count": entry.usage_count,
        "tokens_saved_estimate": entry.tokens_saved_estimate,
        "summary": entry.summary,
        "template_payload": entry.template_payload,
    }, ensure_ascii=False)


async def _solution_bank_stats(ctx: Context, args: dict) -> str:
    stats = solution_bank.get_stats()
    return json.dumps(stats, ensure_ascii=False)


async def _solution_bank_refine(ctx: Context, args: dict) -> str:
    sol_id = _text(args, "solution_id", 80)
    note = _text(args, "note", 500, required=False) or "Automated refinement"
    payload = args.get("optimized_payload") if isinstance(args.get("optimized_payload"), dict) else {}

    refined = solution_bank.refine_solution(sol_id, payload, improvement_note=note)
    if not refined:
        return json.dumps({"status": "error", "message": f"Soluzione {sol_id} non trovata."}, ensure_ascii=False)

    return json.dumps({
        "status": "refined",
        "solution_id": refined.solution_id,
        "optimization_generation": refined.optimization_generation,
        "quality_score": refined.quality_score,
    }, ensure_ascii=False)


TOOLS = {
    "solution_bank_query": Tool(
        name="solution_bank_query",
        description="Interroga il database interno delle soluzioni Nuxiva per recuperare pattern già risolti a zero token.",
        args={"query": "string", "domain": "optional string"},
        capability="read",
        run=_solution_bank_query,
    ),
    "solution_bank_stats": Tool(
        name="solution_bank_stats",
        description="Restituisce le metriche del database interno: numero di soluzioni memorizzate, token risparmiati ed efficienza.",
        args={},
        capability="read",
        run=_solution_bank_stats,
    ),
    "solution_bank_refine": Tool(
        name="solution_bank_refine",
        description="Perfeziona e ottimizza una soluzione esistente nel database interno incrementandone l'indice di qualità.",
        args={"solution_id": "string", "optimized_payload": "object", "note": "optional string"},
        capability="execute",
        run=_solution_bank_refine,
    ),
}
