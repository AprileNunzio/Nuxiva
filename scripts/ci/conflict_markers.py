import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKER = re.compile(rb"^(<<<<<<< |>>>>>>> |=======$)", re.MULTILINE)
SKIP_PARTS = {"dist", "node_modules", "target", "vendor"}
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".wasm", ".so", ".whl", ".gz", ".zip", ".apk", ".pdf", ".md", ".rst"}


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def main() -> int:
    problems = []
    for path in tracked():
        if SKIP_PARTS.intersection(path.parts) or path.suffix.lower() in SKIP_SUFFIX:
            continue
        full = ROOT / path
        if not full.is_file():
            continue
        data = full.read_bytes()
        if b"\0" in data[:2048]:
            continue
        for match in MARKER.finditer(data):
            line = data.count(b"\n", 0, match.start()) + 1
            if match.group(1) == b"=======" and not (b"<<<<<<< " in data and b">>>>>>> " in data):
                continue
            problems.append(f"{path.as_posix()}:{line}: marcatore di conflitto git / git conflict marker")
    for problem in problems:
        print(f"::error file={problem.split(':', 1)[0]}::{problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
