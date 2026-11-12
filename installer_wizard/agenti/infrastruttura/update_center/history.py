from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from config import STATE_DIR

log = logging.getLogger(__name__)

UPDATE_HISTORY_FILE = STATE_DIR / "update_history.json"
MAX_HISTORY_RECORDS = 200

# Format used with git log:
# %H  = commit hash
# %an = author name
# %ct = committer date, UNIX timestamp
# %s  = subject (title)
# %B  = raw body (unwrapped subject and body)
GIT_RECORD_SEP = "\x1e"
GIT_FIELD_SEP = "\x1f"
GIT_LOG_FORMAT = f"%H{GIT_FIELD_SEP}%an{GIT_FIELD_SEP}%ct{GIT_FIELD_SEP}%s{GIT_FIELD_SEP}%B{GIT_RECORD_SEP}"


def _format_iso(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def parse_commit_records(raw: str) -> List[Dict[str, Any]]:
    if not raw or not raw.strip():
        return []
    records: List[Dict[str, Any]] = []
    chunks = raw.split(GIT_RECORD_SEP)
    for chunk in chunks:
        chunk = chunk.strip("\r\n")
        if not chunk:
            continue
        parts = chunk.split(GIT_FIELD_SEP)
        if len(parts) < 5:
            continue
        sha = parts[0].strip()
        author = parts[1].strip()
        ts_str = parts[2].strip()
        title = parts[3].strip()
        body = parts[4].strip()
        try:
            ts = float(ts_str)
        except (ValueError, TypeError):
            ts = 0.0

        if not sha:
            continue

        records.append({
            "sha": sha,
            "short_sha": sha[:7],
            "author": author,
            "timestamp": ts,
            "date_iso": _format_iso(ts) if ts > 0 else "",
            "title": title,
            "body": body,
        })
    return records


async def extract_commits(git_fn: Callable[..., Any], from_rev: Optional[str], to_rev: str) -> List[Dict[str, Any]]:
    if not to_rev:
        return []
    to_rev = to_rev.strip()
    from_rev = from_rev.strip() if from_rev else None

    # If from_rev is valid and distinct, attempt range from_rev..to_rev
    if from_rev and from_rev != to_rev:
        code, out = await git_fn("log", f"--format={GIT_LOG_FORMAT}", f"{from_rev}..{to_rev}")
        if code == 0 and out.strip():
            parsed = parse_commit_records(out)
            if parsed:
                return parsed

    # Fallback: single target commit if range is not possible, unreachable or returned empty
    code, out = await git_fn("log", "-1", f"--format={GIT_LOG_FORMAT}", to_rev)
    if code == 0 and out.strip():
        return parse_commit_records(out)

    return []


def load_history() -> List[Dict[str, Any]]:
    if not UPDATE_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(UPDATE_HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            records = data.get("records", [])
            if isinstance(records, list):
                return records
        elif isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.warning("Impossibile leggere la cronologia aggiornamenti da %s: %s", UPDATE_HISTORY_FILE, exc)
    return []


def save_history(records: List[Dict[str, Any]]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        trimmed = records[:MAX_HISTORY_RECORDS]
        payload = {
            "version": 1,
            "updated_at": _format_iso(time.time()),
            "records": trimmed,
        }
        content = json.dumps(payload, indent=2, ensure_ascii=False)
        # Atomic write
        fd, tmp_path = tempfile.mkstemp(prefix=".nuxiva-upd-hist-", dir=STATE_DIR, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, UPDATE_HISTORY_FILE)
    except OSError as exc:
        log.error("Errore durante il salvataggio della cronologia aggiornamenti: %s", exc)


async def record_update(
    git_fn: Callable[..., Any],
    to_rev: str,
    from_rev: Optional[str] = None,
    status: str = "installed",
    reason: Optional[str] = None,
    error: Optional[str] = None,
    installed_at: Optional[float] = None,
) -> Dict[str, Any]:
    if not to_rev:
        raise ValueError("to_rev è obbligatorio")

    ts = float(installed_at) if installed_at and installed_at > 0 else time.time()
    clean_to = to_rev.strip()
    clean_from = from_rev.strip() if from_rev else None

    history = load_history()

    # Deduplication check:
    # If the exact same installation transition (or same to_rev completed) was already recorded
    # recently (within last 24h), do not duplicate it.
    for existing in history:
        if (
            existing.get("status") == status
            and existing.get("to_rev") == clean_to
            and existing.get("from_rev") == clean_from
            and abs(float(existing.get("installed_at", 0)) - ts) < 86400
        ):
            return existing

    commits: List[Dict[str, Any]] = []
    try:
        commits = await extract_commits(git_fn, clean_from, clean_to)
    except Exception as exc:
        log.warning("Errore durante l'estrazione dei commit per %s..%s: %s", clean_from, clean_to, exc)

    record_id = f"{clean_to[:12]}_{int(ts)}"
    record: Dict[str, Any] = {
        "id": record_id,
        "status": status,
        "from_rev": clean_from,
        "to_rev": clean_to,
        "from_short": clean_from[:7] if clean_from else None,
        "to_short": clean_to[:7],
        "installed_at": ts,
        "installed_at_iso": _format_iso(ts),
        "reason": reason or "automatico",
        "commits": commits,
        "commit_count": len(commits),
        "error": error,
    }

    # Insert newest record at the top
    history.insert(0, record)
    save_history(history)
    return record


def get_history_page(offset: int = 0, limit: int = 20) -> Dict[str, Any]:
    history = load_history()
    total = len(history)
    safe_offset = max(0, offset)
    safe_limit = max(1, min(limit, 100))
    paged = history[safe_offset : safe_offset + safe_limit]
    return {
        "records": paged,
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
    }
