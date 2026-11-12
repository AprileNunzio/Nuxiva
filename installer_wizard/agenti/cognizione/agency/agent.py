import asyncio
import json
from dataclasses import dataclass

from agenti.agency import cognition, prompts, tools
from agenti.agency.text import clean, estimate_tokens
from agenti.brain import llm

MAX_STEPS = 14
STEP_TOKENS = 3000
HISTORY_CHARS = 14000
ARG_PREVIEW = 300
MAX_BATCH = 6


@dataclass
class Outcome:
    summary: str
    tokens: int
    steps: int


def _preview(args: dict) -> dict:
    return {k: (v[:ARG_PREVIEW] + "…" if isinstance(v, str) and len(v) > ARG_PREVIEW else v) for k, v in args.items()}


def _history(entries: list[dict]) -> str:
    text = ""
    for entry in reversed(entries):
        block = json.dumps(entry, ensure_ascii=False) + "\n"
        if len(text) + len(block) > HISTORY_CHARS:
            break
        text = block + text
    return text


async def _run_batch(ctx: tools.Context, raw_batch: list) -> list[dict]:
    items = [item for item in raw_batch if isinstance(item, dict)][:MAX_BATCH]
    if not items:
        return []
    action_specs = []
    by_id: dict[str, tuple[str | None, dict]] = {}
    for idx, item in enumerate(items):
        aid = f"a{idx}"
        tname = item.get("tool")
        targs = item.get("args") if isinstance(item.get("args"), dict) else {}
        by_id[aid] = (tname, targs)
        path = str(targs.get("path", f"__virtual_{idx}__"))
        mutates = tname in ("write_file", "replace_content", "forge_tool")
        action_specs.append({"id": aid, "tool": str(tname or ""), "target_path": path, "mutates": mutates})
    plan = cognition.plan_parallel_batch(action_specs)
    results = []
    for wave in plan.get("waves", []):
        coros = [tools.call(ctx, by_id[aid][0], by_id[aid][1]) for aid in wave if aid in by_id]
        observations = await asyncio.gather(*coros)
        for aid, obs in zip((a for a in wave if a in by_id), observations):
            tname, targs = by_id[aid]
            results.append({"tool": tname, "args": _preview(targs), "observation": obs})
    return results


async def act(brief: dict, task: dict, ctx: tools.Context) -> Outcome:
    history: list[dict] = []
    tokens = 0
    for step in range(1, MAX_STEPS + 1):
        prompt = prompts.act(brief, task, tools.manifest(), _history(history), step, MAX_STEPS)
        reply = await llm.generate(prompt, as_json=True, max_tokens=STEP_TOKENS, temperature=0.2, kind="deep",
                                   system=prompts.AGENT, component="agency_worker")
        tokens += estimate_tokens(prompt, json.dumps(reply, ensure_ascii=False) if reply else "")
        data = reply if isinstance(reply, dict) else {}
        if data.get("final"):
            return Outcome(clean(data["final"], 20000), tokens, step)
        if isinstance(data.get("batch"), list) and data.get("batch"):
            batch_res = await _run_batch(ctx, data["batch"])
            history.append({"step": step, "thought": clean(data.get("thought"), 600), "batch": batch_res})
            continue
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        observation = await tools.call(ctx, data.get("tool"), args)
        history.append({"step": step, "thought": clean(data.get("thought"), 600), "tool": data.get("tool"),
                        "args": _preview(args), "observation": observation})
    return Outcome("", tokens, MAX_STEPS)

