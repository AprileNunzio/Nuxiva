import json

from agenti.brain.llm import BrainUnavailable, generate

COMPONENT = "reason_engine"
UNDERSTAND_TOKENS = 700
PLAN_TOKENS = 900
TIMEOUT = 45


class ModelFailed(RuntimeError):
    pass


def _system(request: dict) -> str:
    return f"{request['system']}\nJSON schema:\n{request['schema']}"


def _prompt(request: dict) -> str:
    external = request.get("external")
    return f"{request['user']}\n\n{external}" if external else request["user"]


def tokens(*texts: str) -> int:
    return sum(len(t.encode("utf-8")) for t in texts if t) // 4


async def _ask(request: dict, max_tokens: int, privacy: str) -> tuple[str, int]:
    prompt, system = _prompt(request), _system(request)
    try:
        data = await generate(prompt, as_json=True, max_tokens=max_tokens, temperature=0.0, kind="chat", system=system,
                              timeout=TIMEOUT, govern=False, component=COMPONENT, privacy=privacy)
    except (BrainUnavailable, ValueError) as exc:
        raise ModelFailed(str(exc)) from exc
    if not isinstance(data, dict):
        raise ModelFailed("reason.model.not_object")
    raw = json.dumps(data, ensure_ascii=False)
    return raw, tokens(prompt, system, raw)


async def understand(request: dict, privacy: str = "") -> tuple[str, int]:
    return await _ask(request, UNDERSTAND_TOKENS, privacy)


async def plan(request: dict, privacy: str = "") -> tuple[str, int]:
    return await _ask(request, PLAN_TOKENS, privacy)
