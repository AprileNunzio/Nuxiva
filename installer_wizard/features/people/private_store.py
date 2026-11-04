import os
from pathlib import Path

from config import ETC_DIR
from sealed import SealedFile, write_private

from features.people.schema import SECTIONS

KEY_FILE = ETC_DIR / "people.key"
EXTRA_PRIVATE = ("mood_journal",)
PRIVATE_KEYS = frozenset({f["key"] for s in SECTIONS if s.get("private") for f in s["fields"]} | set(EXTRA_PRIVATE))


def _sealed(folder: Path, slug: str) -> SealedFile:
    return SealedFile(folder / f"{slug}.private", KEY_FILE)


def split(profile: dict) -> tuple[dict, dict]:
    public = {k: v for k, v in profile.items() if k not in PRIVATE_KEYS}
    private = {k: v for k, v in profile.items() if k in PRIVATE_KEYS}
    return public, private


def load(folder: Path, slug: str) -> dict:
    return _sealed(folder, slug).load()


def save(folder: Path, slug: str, private: dict) -> None:
    sealed = _sealed(folder, slug)
    if private:
        sealed.save(private)
    elif sealed.data_path.exists():
        sealed.data_path.unlink()


def write_public(path: Path, data: bytes) -> None:
    write_private(path, data)


def remove(folder: Path, slug: str) -> None:
    target = folder / f"{slug}.private"
    if target.exists():
        os.remove(target)
