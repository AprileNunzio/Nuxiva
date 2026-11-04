from pathlib import Path


def icon_file(manifest: dict) -> Path | None:
    """Resolve only an owned PNG, never an arbitrary manifest-supplied path."""
    if manifest.get("icon3d") != "./icon.png" or not manifest.get("dir"):
        return None
    root = Path(manifest["dir"]).resolve()
    asset = (root / "icon.png").resolve()
    return asset if asset.is_relative_to(root) and asset.is_file() else None
