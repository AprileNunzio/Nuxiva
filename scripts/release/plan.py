import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import version as versions

ROOT = versions.ROOT
TAG = re.compile(r"^(?:assistant-|android-)?v(\d+\.\d+\.\d+)$")
RELEVANT = (
    "client_apk/",
    "client_satellite/windows_assistant/",
    "native/crates/wakeword-core/",
    "native/crates/wakeword-jni/",
    "scripts/android/",
    "scripts/release/",
    ".github/workflows/android.yml",
    ".github/workflows/windows-assistant.yml",
    ".github/workflows/release.yml",
)
BOT_PREFIX = "release:"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def key(text: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in text.split("."))
    return major, minor, patch


def known_tags() -> list[tuple[tuple[int, int, int], str, str]]:
    found = []
    for tag in git("tag", "--list").split():
        match = TAG.fullmatch(tag)
        if match:
            found.append((key(match.group(1)), match.group(1), tag))
    return sorted(found)


def tag_exists(tag: str) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}"], capture_output=True).returncode == 0


def next_version(tags: list, current: str, part: str) -> str:
    newest = max([key(current)] + [item[0] for item in tags])
    return versions.bumped(".".join(str(n) for n in newest), part)


def previous_tag(tags: list) -> str:
    unified = [item for item in tags if item[2].startswith("v")]
    pool = unified or tags
    return pool[-1][2] if pool else ""


def changed(previous: str, head: str) -> bool:
    if not previous or not tag_exists(previous):
        return True
    paths = git("diff", "--name-only", previous, head).split()
    return any(path.startswith(RELEVANT) for path in paths)


def decide(head: str, force: bool, part: str) -> dict[str, str]:
    tags = known_tags()
    previous = previous_tag(tags)
    subject = git("log", "-1", "--format=%s", head).strip()
    needed = force or (not subject.startswith(BOT_PREFIX) and changed(previous, head))
    return {
        "needed": "true" if needed else "false",
        "version": next_version(tags, versions.read_version(), part) if needed else "",
        "previous_tag": previous,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="plan")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--part", choices=("patch", "minor", "major"), default="patch")
    args = parser.parse_args(argv)
    result = decide(git("rev-parse", args.head).strip(), args.force, args.part)
    lines = [f"{name}={value}" for name, value in result.items()]
    print("\n".join(lines))
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
