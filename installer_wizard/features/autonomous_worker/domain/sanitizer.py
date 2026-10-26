import html
from pathlib import Path
import re
from typing import Any
from features.autonomous_worker.domain.exceptions import MissionValidationError

SAFE_TEXT_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


def sanitize_text(text: Any, max_len: int = 4000) -> str:
    if not isinstance(text, str):
        text = str(text or "")
    cleaned = SAFE_TEXT_RE.sub("", text)
    cleaned = html.escape(cleaned.strip(), quote=True)
    return cleaned[:max_len]


def validate_identifier(val: str, name: str = "id") -> str:
    cleaned = str(val or "").strip()
    if not IDENTIFIER_RE.match(cleaned):
        raise MissionValidationError(f"Invalid {name}: {cleaned}")
    return cleaned


def resolve_safe_path(base_dir: Path, target_relative: str) -> Path:
    target_clean = Path(str(target_relative).strip().lstrip("/\\"))
    resolved = (base_dir / target_clean).resolve()
    base_resolved = base_dir.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise MissionValidationError(f"Path traversal detected: {target_relative}")
    return resolved
