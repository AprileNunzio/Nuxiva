import ast
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOW_FILE = Path(__file__).with_name("fs_boundary_allow.txt")
BASE = "installer_wizard/agenti/"
BANNED_CALLS = {"open"}
BANNED_METHODS = {"read_text", "read_bytes", "write_text", "write_bytes", "unlink", "rmdir", "rename", "touch", "iterdir", "rglob", "glob", "mkdir"}
BANNED_MODULES = {"shutil"}
BANNED_OS = {"remove", "unlink", "rmdir", "rename", "makedirs", "mkdir", "listdir", "scandir", "walk"}


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def in_scope(path: Path) -> bool:
    text = path.as_posix()
    if path.suffix != ".py" or not text.startswith(BASE) or "/tests/" in text or "/test_" in text:
        return False
    return path.name.startswith("tools") or "algorithms" in path.parts


def violations(source: str) -> int:
    count = 0
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            count += sum(1 for alias in node.names if alias.name.split(".")[0] in BANNED_MODULES)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in BANNED_MODULES:
            count += 1
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BANNED_CALLS:
                count += 1
            elif isinstance(func, ast.Attribute):
                owner = func.value.id if isinstance(func.value, ast.Name) else ""
                if func.attr in BANNED_METHODS or (owner == "os" and func.attr in BANNED_OS):
                    count += 1
    return count


def allowances() -> dict[str, tuple[int, datetime.date]]:
    rows: dict[str, tuple[int, datetime.date]] = {}
    for raw in ALLOW_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            name, count, until = line.rsplit(" ", 2)
            rows[name] = (int(count), datetime.date.fromisoformat(until))
    return rows


def main(today: datetime.date | None = None) -> int:
    today = today or datetime.date.today()
    allowed = allowances()
    problems: list[str] = []
    seen: set[str] = set()
    for path in tracked():
        if not in_scope(path) or not (ROOT / path).is_file():
            continue
        key = path.as_posix()
        found = violations((ROOT / path).read_text(encoding="utf-8"))
        if key in allowed:
            seen.add(key)
            frozen, until = allowed[key]
            if until < today:
                problems.append(f"{key}: the exception expired on {until}: move the file access behind the MCP filesystem server")
            elif found > frozen:
                problems.append(f"{key}: {found} direct file accesses, frozen at {frozen}: use the MCP filesystem server instead")
            elif found == 0:
                problems.append(f"{key}: no direct file access left, remove it from {ALLOW_FILE.name}")
        elif found:
            problems.append(f"{key}: {found} direct file accesses outside the MCP filesystem server")
    problems.extend(f"{key}: listed in {ALLOW_FILE.name} but no longer tracked" for key in sorted(set(allowed) - seen))
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
