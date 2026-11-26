import time
from dataclasses import dataclass

import httpx

from agenti.cloud.address import normalize
from agenti.cloud.catalog import BY_ID, REASONING_BUDGET, Provider, parse_ref
from agenti.cloud.failure import describe
from agenti.cloud.pool import shared
from agenti.cloud.studio import harden
from agenti.cloud.vault import vault
from agenti.brain.usage.ledger import usage_ledger


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
    base = (normalize(entry.get("base_url", "")) or spec.base_url).rstrip("/")
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


def _limit(opts: dict, asked: int | None) -> int | None:
    cap = int(opts.get("max_tokens") or 0)
    if asked is None:
        return cap or None
    return min(asked, cap) if cap else asked


def _openai_body(spec: Provider, model: str, messages: list, system: str, max_tokens: int | None, temperature, opts: dict,
                 json_mode: bool) -> dict:
    body = {"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + messages}
    limit = _limit(opts, max_tokens)
    if limit is not None:
        body[spec.token_param] = limit
    temp = opts.get("temperature") or (None if temperature is None else str(temperature))
    if temp not in (None, ""):
        body["temperature"] = float(temp)
    if opts.get("top_p"):
        body["top_p"] = float(opts["top_p"])
    if spec.reasoning and opts.get("reasoning"):
        body["reasoning_effort"] = opts["reasoning"]
    elif spec.id in THINKING_HEADROOM:
        body["reasoning_effort"] = "low"
    if spec.id in THINKING_HEADROOM and limit is not None:
        body[spec.token_param] += THINKING_HEADROOM[spec.id]
    if json_mode and spec.json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def _anthropic_body(model: str, messages: list, system: str, max_tokens: int | None, temperature, opts: dict,
                    json_mode: bool, model_limit: int | None = None) -> dict:
    limit = _limit(opts, max_tokens) or model_limit or RETRY_TOKENS
    if json_mode:
        system = (system + "\n" if system else "") + "Rispondi esclusivamente con un oggetto JSON valido."
    body = {"model": model, "messages": messages, "max_tokens": limit}
    if system:
        body["system"] = system
    budget = REASONING_BUDGET.get(opts.get("reasoning", ""))
    if budget and (model_limit is None or budget < model_limit):
        body["thinking"] = {"type": "enabled", "budget_tokens": budget}
        body["max_tokens"] = min(limit + budget, model_limit) if model_limit else limit + budget
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


def _input_tokens(spec: Provider, data: dict) -> int:
    usage = data.get("usage") or {}
    return int(usage.get("input_tokens" if spec.kind == "anthropic" else "prompt_tokens") or 0)


def _cut(spec: Provider, data: dict) -> bool:
    if spec.kind == "anthropic":
        return data.get("stop_reason") in CUT
    return str((data.get("choices") or [{}])[0].get("finish_reason") or "") in CUT


MODEL_LIMIT_TTL = 6 * 3600.0
_model_limits: dict[tuple[str, str], tuple[float, int | None]] = {}


async def _post(url: str, body: dict, head: dict, timeout: float) -> httpx.Response:
    return await shared().post(url, json=body, headers=head, timeout=timeout)


async def _anthropic_model_limit(root: str, model: str, head: dict) -> int | None:
    from urllib.parse import quote

    key = (root, model)
    cached = _model_limits.get(key)
    if cached and time.monotonic() - cached[0] < MODEL_LIMIT_TTL:
        return cached[1]
    try:
        response = await shared().get(f"{root}/models/{quote(model, safe='')}", headers=head, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    limit = data.get("max_tokens") if isinstance(data, dict) else None
    limit = limit if type(limit) is int and limit > 0 else None
    _model_limits[key] = (time.monotonic(), limit)
    return limit


@dataclass
class Request:
    pid: str
    model: str
    spec: Provider
    url: str
    body: dict
    head: dict
    timeout: float


async def prepare(ref: str, messages: list[dict], system: str, max_tokens: int | None, temperature, json_mode: bool) -> Request:
    pid, model = parse_ref(ref)
    spec, entry = BY_ID[pid], vault.get(pid)
    if not vault.configured(pid):
        raise CloudError(f"{spec.name}: servizio non configurato")
    if not usage_ledger.allows(ref):
        raise CloudError(f"{spec.name}: limite di consumo mensile raggiunto", 429)
    opts = entry.get("options", {})
    head, timeout = headers(spec, entry), float(opts.get("timeout") or 120)
    if spec.kind == "anthropic":
        root = endpoint(spec, entry)
        model_limit = await _anthropic_model_limit(root, model, head) if max_tokens is None and not opts.get("max_tokens") else None
        body = _anthropic_body(model, messages, system, max_tokens, temperature, opts, json_mode, model_limit)
        return Request(pid, model, spec, f"{root}/messages", body, head, timeout)
    body = harden(_openai_body(spec, model, messages, system, max_tokens, temperature, opts, json_mode), entry)
    return Request(pid, model, spec, f"{endpoint(spec, entry)}/chat/completions", body, head, timeout)


async def complete(ref: str, messages: list[dict], system: str = "", max_tokens: int | None = 800, temperature=None,
                   json_mode: bool = False, _retried: bool = False) -> Reply:
    request = await prepare(ref, messages, system, max_tokens, temperature, json_mode)
    pid, model, spec, url, body, head, timeout = (request.pid, request.model, request.spec, request.url, request.body,
                                                  request.head, request.timeout)
    started = time.perf_counter()
    try:
        res = await _post(url, body, head, timeout)
        elapsed = (time.perf_counter() - started) * 1000
        if pid == "openrouter":
            from agenti.brain.free_router.failover_engine import observe
            observe(ref, dict(res.headers), res.status_code, elapsed)
        if res.status_code == 400 and spec.kind != "anthropic":
            for extra in ("response_format", "temperature", "top_p", "reasoning_effort"):
                body.pop(extra, None)
            res = await _post(url, body, head, timeout)
            if pid == "openrouter":
                from agenti.brain.free_router.failover_engine import observe
                observe(ref, dict(res.headers), res.status_code, (time.perf_counter() - started) * 1000)
    except httpx.HTTPError as exc:
        if pid == "openrouter":
            from agenti.brain.free_router.failover_engine import failed
            failed(ref, 503)
        raise CloudError(f"{spec.name}: {type(exc).__name__}", 503) from exc
    if res.status_code >= 400:
        raise CloudError(describe(f"{spec.name} · {model}", url, res), res.status_code, dict(res.headers))
    try:
        data = res.json()
    except (ValueError, KeyError) as exc:
        raise CloudError(f"{spec.name}: risposta non valida dal server ({exc})", res.status_code) from exc
    if _cut(spec, data) and json_mode:
        if _retried or max_tokens is None:
            raise CloudError(f"{spec.name}: risposta troncata dal limite di lunghezza")
        return await complete(ref, messages, system, min(RETRY_TOKENS, max(max_tokens * 3, 1500)), temperature, json_mode, True)
    text, tokens = _text(spec, data)
    usage_ledger.record(ref, _input_tokens(spec, data), tokens)
    if not text.strip():
        raise CloudError(f"{spec.name}: risposta vuota")
    return Reply(text=text.strip(), model=ref, ms=(time.perf_counter() - started) * 1000, tokens=tokens)
