import json
from dataclasses import dataclass

from features.agency import prompts, tools
from features.agency.text import clean, estimate_tokens
from features.brain import llm

MAX_STEPS = 14
STEP_TOKENS = 3000
HISTORY_CHARS = 14000
ARG_PREVIEW = 300


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
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        observation = await tools.call(ctx, data.get("tool"), args)
        history.append({"step": step, "thought": clean(data.get("thought"), 600), "tool": data.get("tool"),
                        "args": _preview(args), "observation": observation})
    return Outcome("", tokens, MAX_STEPS)
