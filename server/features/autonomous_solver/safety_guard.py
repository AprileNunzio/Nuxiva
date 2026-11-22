import re
from pathlib import Path


FORBIDDEN_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/\s*($|;|\|)"),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=/dev/(zero|random|urandom)\s+of=/dev/", re.IGNORECASE),
    re.compile(r"\bFormat-Volume\b", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b.*-Recurse.*-Force\s+[A-Za-z]:\\", re.IGNORECASE),
    re.compile(r"\bshutdown\b|\breboot\b|\bpoweroff\b", re.IGNORECASE),
]


class SafetyViolationError(ValueError):
    pass


def validate_command_safety(command: str) -> None:
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.search(command):
            raise SafetyViolationError(
                f"Comando bloccato dal guardrail Zero-Trust di sicurezza: '{command[:120]}'"
            )


def safe_script_path(workspace: Path, filename: str) -> Path:
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise SafetyViolationError(f"Nome file script non sicuro: '{filename}'")
    resolved = (workspace / filename).resolve()
    if workspace.resolve() not in resolved.parents:
        raise SafetyViolationError(f"Path traversal rilevato per '{filename}'")
    return resolved
