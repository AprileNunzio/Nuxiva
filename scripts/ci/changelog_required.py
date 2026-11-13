import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REV = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
NOTE = re.compile(r"^changelog/[0-9]{14}-[a-z0-9]+(?:-[a-z0-9]+)*\.json$")
NULL = re.compile(r"^0+$")
GENERATED = ("client_web/dist/",)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def exists(rev: str) -> bool:
    probe = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{rev}^{{commit}}"], capture_output=True)
    return probe.returncode == 0


def commits(base: str, head: str) -> list[str]:
    if REV.match(base) and not NULL.match(base) and exists(base):
        return git("rev-list", "--no-merges", f"{base}..{head}").split()
    return [head]


def paths(sha: str, *flags: str) -> list[str]:
    out = git("diff-tree", "--no-commit-id", "--root", "--name-only", "-r", "-z", *flags, sha)
    return [path for path in out.split("\0") if path]


def has_note(sha: str) -> bool:
    changed = paths(sha)
    if changed and all(path.startswith(GENERATED) for path in changed):
        return True
    return any(NOTE.match(path) for path in paths(sha, "--diff-filter=A"))


def main(argv: list[str]) -> int:
    base = argv[1].strip().lower() if len(argv) > 1 else ""
    head = argv[2].strip().lower() if len(argv) > 2 else ""
    if not REV.match(head):
        print("::error::revisione HEAD non valida / invalid HEAD revision")
        return 2
    missing = [sha for sha in commits(base, head) if not has_note(sha)]
    for sha in missing:
        subject = git("log", "-1", "--format=%s", sha).strip()[:120]
        print(f"::error::{sha[:12]} senza nota di rilascio in changelog/ / missing release note in changelog/: {subject}")
    if missing:
        print("Ogni commit deve aggiungere un file changelog/AAAAMMGGhhmmss-slug.json con Novità e Bugfix.")
        print("Every commit must add a changelog/YYYYMMDDhhmmss-slug.json file with features and fixes.")
        return 1
    print("Note di rilascio presenti per ogni commit / Release notes present for every commit")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
