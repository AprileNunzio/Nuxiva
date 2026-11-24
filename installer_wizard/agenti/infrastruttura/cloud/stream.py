import json
import time
from collections.abc import Callable

import httpx

from agenti.brain.usage.ledger import usage_ledger
from agenti.cloud.client import CloudError, Reply, complete, prepare
from agenti.cloud.failure import describe
from agenti.cloud.pool import shared

PREFIX = "data:"
DONE = "[DONE]"
FALLBACK = frozenset({400, 404, 405, 415, 422})
MAX_CHARS = 400_000

Piece = tuple[str, int, int]


def openai_piece(event: dict) -> Piece:
    choice = (event.get("choices") or [{}])[0] or {}
    text = (choice.get("delta") or {}).get("content") or ""
    usage = event.get("usage") or {}
    return str(text), int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


def anthropic_piece(event: dict) -> Piece:
    kind = event.get("type")
    if kind == "error":
        detail = (event.get("error") or {}).get("message") or "errore del servizio"
        raise CloudError(f"Anthropic: {str(detail)[:200]}", 502)
    if kind == "content_block_delta":
        delta = event.get("delta") or {}
        return (str(delta.get("text") or "") if delta.get("type") == "text_delta" else ""), 0, 0
    if kind == "message_start":
        usage = (event.get("message") or {}).get("usage") or {}
        return "", int(usage.get("input_tokens") or 0), 0
    if kind == "message_delta":
        return "", 0, int((event.get("usage") or {}).get("output_tokens") or 0)
    return "", 0, 0


def decode(line: str) -> dict | None:
    if not line.startswith(PREFIX):
        return None
    data = line[len(PREFIX):].strip()
    if not data or data == DONE:
        return None
    try:
        event = json.loads(data)
    except ValueError as exc:
        raise CloudError(f"risposta in streaming non valida ({exc})", 502) from exc
    return event if isinstance(event, dict) else None


def _observe(ref: str, res: httpx.Response, started: float) -> None:
    if ref.startswith("cloud:openrouter/"):
        from agenti.brain.free_router.failover_engine import observe
        observe(ref, dict(res.headers), res.status_code, (time.perf_counter() - started) * 1000)


async def complete_stream(ref: str, messages: list[dict], system: str = "", max_tokens: int | None = 800, temperature=None,
                          on_token: Callable[[str], None] | None = None) -> Reply:
    request = await prepare(ref, messages, system, max_tokens, temperature, False)
    spec = request.spec
    piece = anthropic_piece if spec.kind == "anthropic" else openai_piece
    started = time.perf_counter()
    parts: list[str] = []
    size, tokens_in, tokens_out, fallback = 0, 0, 0, False
    try:
        async with shared().stream("POST", request.url, json={**request.body, "stream": True}, headers=request.head,
                                   timeout=request.timeout) as res:
            _observe(ref, res, started)
            if res.status_code in FALLBACK:
                fallback = True
            elif res.status_code >= 400:
                await res.aread()
                raise CloudError(describe(f"{spec.name} · {request.model}", request.url, res), res.status_code, dict(res.headers))
            else:
                async for line in res.aiter_lines():
                    event = decode(line)
                    if event is None:
                        continue
                    text, used_in, used_out = piece(event)
                    tokens_in, tokens_out = max(tokens_in, used_in), max(tokens_out, used_out)
                    if not text:
                        continue
                    size += len(text)
                    if size > MAX_CHARS:
                        raise CloudError(f"{spec.name}: risposta oltre il limite di lunghezza", 502)
                    parts.append(text)
                    if on_token is not None:
                        on_token(text)
    except httpx.HTTPError as exc:
        raise CloudError(f"{spec.name}: {type(exc).__name__}", 503) from exc
    if fallback:
        answer = await complete(ref, messages, system, max_tokens, temperature)
        if on_token is not None:
            on_token(answer.text)
        return answer
    text = "".join(parts).strip()
    usage_ledger.record(ref, tokens_in, tokens_out or max(1, len(text) // 4))
    if not text:
        raise CloudError(f"{spec.name}: risposta vuota")
    return Reply(text=text, model=ref, ms=(time.perf_counter() - started) * 1000, tokens=tokens_out)
