import http.client
import json
import logging
import time

log = logging.getLogger("nuxiva.compute")
HOST = "127.0.0.1"
PORT = 11434
TIMEOUT = 2.0
BODY_LIMIT = 1 << 20
CACHE_SECONDS = 20.0
GIB = 1 << 30


def _get(path: str) -> dict | None:
    conn = http.client.HTTPConnection(HOST, PORT, timeout=TIMEOUT)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        data = response.read(BODY_LIMIT)
        if response.status != 200:
            return None
        parsed = json.loads(data.decode("utf-8"))
    except ConnectionRefusedError:
        return None
    except (OSError, http.client.HTTPException, ValueError) as exc:
        log.debug("Ollama locale non leggibile (%s): %s", path, exc)
        return None
    finally:
        conn.close()
    return parsed if isinstance(parsed, dict) else None


def _models(payload: dict | None, key: str = "models") -> list[dict]:
    items = (payload or {}).get(key)
    if not isinstance(items, list):
        return []
    return [{"name": str(m["name"]), "size_gb": round(float(m.get("size") or 0) / GIB, 2)}
            for m in items if isinstance(m, dict) and isinstance(m.get("name"), str)]


class OllamaProbe:
    def __init__(self) -> None:
        self.at = 0.0
        self.state: dict = {"available": False, "version": "", "models": [], "running": []}

    def read(self) -> dict:
        if time.monotonic() - self.at < CACHE_SECONDS:
            return self.state
        version = _get("/api/version")
        if version is None:
            self.state = {"available": False, "version": "", "models": [], "running": []}
        else:
            self.state = {"available": True, "version": str(version.get("version") or ""),
                          "models": _models(_get("/api/tags")), "running": _models(_get("/api/ps"))}
        self.at = time.monotonic()
        return self.state
