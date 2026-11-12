from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urlparse

from config import STATE_DIR
from agenti.store.integrity import validate_package_security_contract

log = logging.getLogger("nuxiva.store.repositories")

REPOS_FILE = STATE_DIR / "store_repositories.json"
INSTALLED_CUSTOM_FILE = STATE_DIR / "store_custom_installed.json"

OFFICIAL_REPOSITORY: dict[str, Any] = {
    "id": "official",
    "name": "Repository Ufficiale Nuxiva",
    "url": "builtin://nuxiva-core",
    "description": "Componenti, modelli neurali ed estensioni modulari certificate Nuxiva OS",
    "official": True,
    "enabled": True,
    "created_at": 0,
}


def _ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_repositories() -> list[dict[str, Any]]:
    _ensure_dirs()
    if not REPOS_FILE.is_file():
        return [dict(OFFICIAL_REPOSITORY)]
    try:
        data = json.loads(REPOS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
    except Exception as exc:
        log.warning("Impossibile leggere store_repositories.json: %s", exc)
        data = []

    # Ensure official repo is always first
    cleaned: list[dict[str, Any]] = [dict(OFFICIAL_REPOSITORY)]
    for repo in data:
        if isinstance(repo, dict) and repo.get("id") != "official":
            cleaned.append(repo)
    return cleaned


def save_repositories(repos: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    # Never persist official repo into user custom file or keep it normalized
    custom_only = [r for r in repos if isinstance(r, dict) and r.get("id") != "official"]
    temp_file = STATE_DIR / f".store_repositories_{int(time.time()*1000)}.tmp"
    try:
        temp_file.write_text(json.dumps(custom_only, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_file.replace(REPOS_FILE)
    except Exception as exc:
        log.error("Errore salvataggio repository store: %s", exc)
        if temp_file.is_file():
            temp_file.unlink(missing_ok=True)
        raise


def load_installed_custom() -> set[str]:
    _ensure_dirs()
    if not INSTALLED_CUSTOM_FILE.is_file():
        return set()
    try:
        data = json.loads(INSTALLED_CUSTOM_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def set_custom_package_installed(item_id: str, installed: bool) -> None:
    _ensure_dirs()
    current = load_installed_custom()
    if installed:
        current.add(item_id)
    else:
        current.discard(item_id)

    temp_file = STATE_DIR / f".store_custom_installed_{int(time.time()*1000)}.tmp"
    try:
        temp_file.write_text(json.dumps(sorted(list(current)), indent=2), encoding="utf-8")
        temp_file.replace(INSTALLED_CUSTOM_FILE)
    except Exception as exc:
        log.error("Errore salvataggio pacchetti custom installati: %s", exc)
        if temp_file.is_file():
            temp_file.unlink(missing_ok=True)
        raise


def validate_repository_url(url: str) -> str:
    cleaned = str(url or "").strip()
    if not cleaned:
        raise ValueError("L'URL del repository non puo essere vuoto.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https", "file"):
        raise ValueError("Protocollo non supportato: usare http://, https:// o file://")
    if parsed.hostname in ("169.254.169.254", "metadata.google.internal"):
        raise ValueError("URL riservato non consentito per sicurezza.")
    return cleaned


def add_repository(name: str, url: str, description: str = "", packages: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    name_clean = str(name or "").strip()
    if not name_clean or len(name_clean) > 80:
        raise ValueError("Il nome del repository deve contenere tra 1 e 80 caratteri.")

    url_clean = validate_repository_url(url)
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name_clean.lower())[:32].strip("_") or "custom_repo"

    repos = load_repositories()
    base_id = f"repo_{slug}"
    repo_id = base_id
    counter = 1
    while any(r.get("id") == repo_id for r in repos):
        counter += 1
        repo_id = f"{base_id}_{counter}"

    # Normalize packages if provided
    cached_packages: list[dict[str, Any]] = []
    if packages and isinstance(packages, list):
        for pkg in packages:
            if isinstance(pkg, dict) and pkg.get("id") and pkg.get("title"):
                valid, _ = validate_package_security_contract(pkg)
                if not valid:
                    continue
                cached_packages.append({
                    "id": f"{repo_id}:{pkg['id']}",
                    "raw_id": str(pkg["id"]),
                    "category": str(pkg.get("category", "productivity")),
                    "title": str(pkg["title"]),
                    "description": str(pkg.get("description", "")),
                    "size_gb": float(pkg.get("size_gb", 0.5)),
                    "removable": bool(pkg.get("removable", True)),
                    "install_url": str(pkg.get("install_url", "")),
                    "capabilities": list(pkg.get("capabilities") or []),
                    "allowed_hosts": list(pkg.get("allowed_hosts") or []),
                    "checksum": str(pkg.get("checksum") or pkg.get("integrity") or ""),
                })

    new_repo: dict[str, Any] = {
        "id": repo_id,
        "name": name_clean,
        "url": url_clean,
        "description": str(description or "").strip() or "Repository personale configurato dall'utente",
        "official": False,
        "enabled": True,
        "created_at": time.time(),
        "packages": cached_packages,
        "packages_count": len(cached_packages),
    }

    repos.append(new_repo)
    save_repositories(repos)
    return new_repo


def remove_repository(repo_id: str) -> bool:
    if repo_id == "official":
        raise ValueError("Il repository ufficiale Nuxiva non puo essere rimosso.")
    repos = load_repositories()
    filtered = [r for r in repos if r.get("id") != repo_id]
    if len(filtered) == len(repos):
        return False
    save_repositories(filtered)
    return True


def get_custom_packages() -> list[dict[str, Any]]:
    repos = load_repositories()
    installed = load_installed_custom()
    custom_items: list[dict[str, Any]] = []

    for repo in repos:
        if repo.get("official") or not repo.get("enabled"):
            continue
        repo_id = repo.get("id", "")
        repo_name = repo.get("name", "Repository Personale")
        packages = repo.get("packages", [])
        if isinstance(packages, list):
            for pkg in packages:
                pkg_id = pkg.get("id")
                if not pkg_id:
                    continue
                is_inst = pkg_id in installed
                custom_items.append({
                    "id": pkg_id,
                    "category": pkg.get("category", "productivity"),
                    "title": pkg.get("title", "App"),
                    "description": pkg.get("description", ""),
                    "size_gb": float(pkg.get("size_gb", 0.5)),
                    "installed": is_inst,
                    "removable": True,
                    "source": "custom",
                    "repository_id": repo_id,
                    "repository_name": repo_name,
                })
    return custom_items


def find_custom_package(item_id: str) -> Optional[dict[str, Any]]:
    items = get_custom_packages()
    for it in items:
        if it.get("id") == item_id:
            return it
    return None
