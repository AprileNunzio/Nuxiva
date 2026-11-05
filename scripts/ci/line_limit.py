import subprocess
import sys
from pathlib import Path

LIMIT = 500
ROOT = Path(__file__).resolve().parents[2]
ALLOW_FILE = Path(__file__).with_name("line_limit_allow.txt")
SUFFIXES = {".rs", ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".css"}
SKIP_PARTS = {"dist", "node_modules", "assets", "vendor", "target"}


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def eligible(path: Path) -> bool:
    return path.suffix in SUFFIXES and not SKIP_PARTS.intersection(path.parts) and not path.name.endswith(".min.js")


def count(path: Path) -> int:
    with (ROOT / path).open("rb") as handle:
        return sum(1 for _ in handle)


def allowances() -> dict[str, int]:
    rows: dict[str, int] = {}
    for raw in ALLOW_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        name, _, value = line.rpartition(" ")
        rows[name] = int(value)
    return rows


def main() -> int:
    allowed = allowances()
    problems: list[str] = []
    seen: set[str] = set()
    for path in tracked():
        if not eligible(path) or not (ROOT / path).is_file():
            continue
        key = path.as_posix()
        lines = count(path)
        if key in allowed:
            seen.add(key)
            if lines > allowed[key]:
                problems.append(f"{key}: {lines} lines, frozen at {allowed[key]}: split it instead of growing it")
            elif lines <= LIMIT:
                problems.append(f"{key}: now {lines} lines, remove it from {ALLOW_FILE.name}")
        elif lines > LIMIT:
            problems.append(f"{key}: {lines} lines, limit is {LIMIT}")
    problems.extend(f"{key}: listed in {ALLOW_FILE.name} but no longer tracked" for key in sorted(set(allowed) - seen))
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
