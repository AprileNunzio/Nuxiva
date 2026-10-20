import glob
import json
import logging
from pathlib import Path

from config import FEATURES_DIR

log = logging.getLogger("nuxiva.app_scanner")

APPS_DIR = FEATURES_DIR.parent / "apps"
KNOWN_APP_IDS = {"music", "tv", "models3d", "shares", "terminal", "system_logs", "applications", "explorer", "home_assistant"}


def is_application(manifest: dict, path: str | Path | None = None) -> bool:
    """Verifica se una risorsa è una vera Applicazione autonoma."""
    if manifest.get("kind") == "app":
        return True
    if manifest.get("kind") == "feature":
        return False
    if path:
        p = Path(path)
        if APPS_DIR.exists() and p.is_relative_to(APPS_DIR):
            return True
        if "/apps/" in str(p).replace("\\", "/"):
            return True
    return manifest.get("id") in KNOWN_APP_IDS


def is_feature(manifest: dict, path: str | Path | None = None) -> bool:
    """Verifica se una risorsa è una Funzionalità (modulo/opzione del pannello di controllo)."""
    return not is_application(manifest, path)


def scan_catalog() -> dict[str, list[dict]]:
    """Scansiona tutte le applicazioni e le funzionalità del sistema."""
    apps, features = [], []
    search_paths = []
    if APPS_DIR.exists():
        search_paths.extend(glob.glob(str(APPS_DIR / "*" / "feature.json")))
        search_paths.extend(glob.glob(str(APPS_DIR / "*" / "manifest.json")))
    if FEATURES_DIR.exists():
        search_paths.extend(glob.glob(str(FEATURES_DIR / "*" / "feature.json")))

    seen_ids = set()
    for p in sorted(search_paths):
        try:
            manifest = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Impossibile leggere manifest %s: %s", p, exc)
            continue
        mid = manifest.get("id")
        if not mid or mid in seen_ids:
            continue
        seen_ids.add(mid)
        kind = "app" if is_application(manifest, p) else "feature"
        manifest["kind"] = kind
        manifest["path"] = str(Path(p).parent)
        if kind == "app":
            apps.append(manifest)
        else:
            features.append(manifest)

    return {"apps": apps, "features": features}
