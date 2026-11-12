import hashlib
import shutil
from pathlib import Path


def delete_photo(folder: Path, photo_id: str, kind_of) -> None:
    primary = folder / "photo.jpg"
    photos = folder / "photos"
    target = primary if photo_id in ("photo_primary", "photo.jpg") else photos / photo_id
    if not target.is_file():
        raise FileNotFoundError(photo_id)
    digest = hashlib.sha256(target.read_bytes()).digest()
    candidates = [primary, *photos.glob("*.jpg")]
    matches = [p for p in candidates if p.is_file() and hashlib.sha256(p.read_bytes()).digest() == digest]
    for path in matches:
        path.unlink()
    if not primary.is_file():
        remaining = sorted((p for p in photos.glob("*.jpg") if kind_of(p.stem) not in ("body", "body_back")),
                           key=lambda p: -p.stat().st_mtime)
        if remaining:
            shutil.copyfile(remaining[0], primary)


def clear_samples(folder: Path) -> int:
    removed = 0
    for name in ("embeddings.npy", "embeddings_ir.npy"):
        target = folder / name
        if target.is_file():
            target.unlink()
            removed += 1
    return removed
