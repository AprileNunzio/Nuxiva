import json
from functools import lru_cache
from pathlib import Path

from config import env_get
from fastapi import HTTPException

from features.mind.persistence import MemoryStorageError


@lru_cache(maxsize=4)
def messages(language: str) -> dict:
    language = language if language in {"it", "en", "fr", "es"} else "it"
    return json.loads((Path(__file__).with_name("language") / f"{language}.json").read_text(encoding="utf-8"))["messages"]


def failure(error) -> HTTPException:
    code = "memory_storage_unavailable" if isinstance(error, MemoryStorageError) else str(error)
    if code not in {"invalid_memory", "unknown_memory", "memory_conflict", "memory_full", "memory_storage_unavailable"}:
        code = "invalid_memory"
    status = {"unknown_memory": 404, "memory_conflict": 409, "memory_full": 409, "memory_storage_unavailable": 503}.get(code, 400)
    return HTTPException(status, {"code": code, "message": messages(env_get("NUXIVA_UI_LANG", "it"))[code]})
