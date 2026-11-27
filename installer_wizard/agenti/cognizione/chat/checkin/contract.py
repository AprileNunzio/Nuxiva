import hashlib
import json
import time


def fact(key: str, topic: str, kind: str, priority: int, ttl: int, line: str, params: dict | None = None,
         starts_at: float | None = None, terms: list[str] | None = None) -> dict:
    params = {k: str(v)[:120] for k, v in (params or {}).items()}
    raw = json.dumps([key, line, params], sort_keys=True, ensure_ascii=False)
    return {"key": key, "topic": topic, "kind": kind, "priority": max(0, min(100, int(priority))),
            "signature": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32], "observed_at": int(time.time()),
            "ttl": int(ttl), "starts_at": int(starts_at) if starts_at else None, "terms": (terms or [])[:16],
            "line": line, "params": params}
