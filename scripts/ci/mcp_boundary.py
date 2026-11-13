import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = "installer_wizard/agenti/comunicazione/mcpclient/"
BANNED_MODULES = {"httpx", "requests", "aiohttp", "urllib3", "websockets", "socket", "http", "subprocess"}
BANNED_PREFIXES = ("urllib.request", "urllib.error")
BANNED_NAMES = {"client", "service"}


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def banned(name: str) -> bool:
    return name.split(".")[0] in BANNED_MODULES or name.startswith(BANNED_PREFIXES)


def problems(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if banned(a.name)]
        elif isinstance(node, ast.ImportFrom):
            if banned(node.module or ""):
                found.append(node.module or "")
            if (node.module or "").endswith("mcpclient") and any(a.name in BANNED_NAMES for a in node.names):
                found.append("mcpclient legacy client")
    return found


def main() -> int:
    failed = 0
    for path in tracked():
        text = path.as_posix()
        if path.suffix != ".py" or not text.startswith(SCOPE) or "/tests/" in text:
            continue
        for item in problems((ROOT / path).read_text(encoding="utf-8")):
            failed += 1
            print(f"::error file={text}::logica MCP solo in Rust, import vietato / MCP logic lives in Rust only, banned import: {item}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
