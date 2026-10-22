import time
from dataclasses import dataclass

import httpx

from features.cloud.catalog import BY_ID, REASONING_BUDGET, Provider, parse_ref
from features.cloud.vault import vault


class CloudError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, headers: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = dict(headers or {})


@dataclass
class Reply:
    text: str
    model: str
    ms: float
    tokens: int = 0


def endpoint(spec: Provider, entry: dict) -> str:
    base = (entry.get("base_url") or spec.base_url).rstrip("/")
    if not base:
        raise CloudError(f"{spec.name}: indirizzo del servizio mancante")
    return base


def headers(spec: Provider, entry: dict) -> dict:
    key = entry.get("key", "")
    if spec.kind == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    base = {"content-type": "application/json"}
    if spec.id == "openrouter":
        base.update({"HTTP-Referer": "https://github.com/AprileNunzio/NUXIVA", "X-Title": "Nuxiva OS"})
    if key and spec.auth == "api-key":
        base["api-key"] = key
    elif key:
        base["authorization"] = f"Bearer {key}"
    return base


THINKING_HEADROOM = {"gemini": 2048}
RETRY_TOKENS = 8192
CUT = ("length", "max_tokens", "MAX_TOKENS")


def _limit(opts: dict, asked: int) -> int:
    cap = int(opts.get("max_tokens") or 0)
    return min(asked, cap) if cap else asked


def _openai_body(spec: Provider, model: str, messages: list, system: str, max_tokens: int, temperature, opts: dict,
                 json_mode: bool) -> dict:
    body = {"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + messages,
            spec.token_param: _limit(opts, max_tokens)}
    temp = opts.get("temperature") or (None if temperature is None else str(temperature))
    if temp not in (None, ""):
        body["temperature"] = float(temp)
    if opts.get("top_p"):
        body["top_p"] = float(opts["top_p"])
    if spec.reasoning and opts.get("reasoning"):
        body["reasoning_effort"] = opts["reasoning"]
    elif spec.id in THINKING_HEADROOM:
        body["reasoning_effort"] = "low"
    if spec.id in THINKING_HEADROOM:
        body[spec.token_param] += THINKING_HEADROOM[spec.id]
    if json_mode and spec.json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def _anthropic_body(model: str, messages: list, system: str, max_tokens: int, temperature, opts: dict,
                    json_mode: bool) -> dict:
    limit = _limit(opts, max_tokens)
    if json_mode:
        system = (system + "\n" if system else "") + "Rispondi esclusivamente con un oggetto JSON valido."
    body = {"model": model, "messages": messages, "max_tokens": limit}
    if system:
        body["system"] = system
    budget = REASONING_BUDGET.get(opts.get("reasoning", ""))
    if budget:
        body["thinking"] = {"type": "enabled", "budget_tokens": budget}
        body["max_tokens"] = limit + budget
        return body
    temp = opts.get("temperature") or (None if temperature is None else str(temperature))
    if temp not in (None, ""):
        body["temperature"] = min(float(temp), 1.0)
    if opts.get("top_p") and "temperature" not in body:
        body["top_p"] = float(opts["top_p"])
    return body


def _text(spec: Provider, data: dict) -> tuple[str, int]:
    if spec.kind == "anthropic":
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return text, data.get("usage", {}).get("output_tokens", 0)
    choice = (data.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content") or "", (data.get("usage") or {}).get("completion_tokens", 0)


def _cut(spec: Provider, data: dict) -> bool:
    if spec.kind == "anthropic":
        return data.get("stop_reason") in CUT
    return str((data.get("choices") or [{}])[0].get("finish_reason") or "") in CUT


async def _post(url: str, body: dict, head: dict, timeout: float) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(url, json=body, headers=head)


async def complete(ref: str, messages: list[dict], system: str = "", max_tokens: int = 800, temperature=None,
                   json_mode: bool = False, _retried: bool = False) -> Reply:
    pid, model = parse_ref(ref)
    spec, entry = BY_ID[pid], vault.get(pid)
    if not vault.configured(pid):
        raise CloudError(f"{spec.name}: servizio non configurato")
    opts = entry.get("options", {})
    head, timeout = headers(spec, entry), float(opts.get("timeout") or 120)
    if spec.kind == "anthropic":
        url = f"{endpoint(spec, entry)}/messages"
        body = _anthropic_body(model, messages, system, max_tokens, temperature, opts, json_mode)
    else:
        url = f"{endpoint(spec, entry)}/chat/completions"
        body = _openai_body(spec, model, messages, system, max_tokens, temperature, opts, json_mode)
    started = time.perf_counter()
    try:
        res = await _post(url, body, head, timeout)
        elapsed = (time.perf_counter() - started) * 1000
        if pid == "openrouter":
            from features.brain.free_router.failover_engine import observe
            observe(ref, dict(res.headers), res.status_code, elapsed)
        if res.status_code == 400 and spec.kind != "anthropic":
            for extra in ("response_format", "temperature", "top_p", "reasoning_effort"):
                body.pop(extra, None)
            res = await _post(url, body, head, timeout)
            if pid == "openrouter":
                from features.brain.free_router.failover_engine import observe
                observe(ref, dict(res.headers), res.status_code, (time.perf_counter() - started) * 1000)
    except httpx.HTTPError as exc:
        if pid == "openrouter":
            from features.brain.free_router.failover_engine import failed
            failed(ref, 503)
        raise CloudError(f"{spec.name}: {type(exc).__name__}", 503) from exc
    if res.status_code >= 400:
        raise CloudError(f"{spec.name} {res.status_code}", res.status_code, dict(res.headers))
    try:
        data = res.json()
    except (ValueError, KeyError) as exc:
        raise CloudError(f"{spec.name}: risposta non valida dal server ({exc})", res.status_code) from exc
    if _cut(spec, data) and json_mode:
        if _retried:
            raise CloudError(f"{spec.name}: risposta troncata dal limite di lunghezza")
        return await complete(ref, messages, system, min(RETRY_TOKENS, max(max_tokens * 3, 1500)), temperature, json_mode, True)
    text, tokens = _text(spec, data)
    if not text.strip():
        raise CloudError(f"{spec.name}: risposta vuota")
    return Reply(text=text.strip(), model=ref, ms=(time.perf_counter() - started) * 1000, tokens=tokens)
