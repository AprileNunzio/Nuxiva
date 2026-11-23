import json
import logging
import threading
from dataclasses import dataclass

from updates import fetch, manifest
from updates.errors import UpdateFailure

log = logging.getLogger("nuxiva.updates")
RELEASES = f"https://api.github.com/repos/{manifest.REPOSITORY}/releases?per_page=20"
LIST_LIMIT = 2_000_000


@dataclass(frozen=True)
class Candidate:
    version: str
    tag: str
    assets: dict[str, str]

    @property
    def signed(self) -> bool:
        return bool(self.assets.get("manifest.sig"))


def _assets(release: dict) -> dict[str, str]:
    found = {}
    for asset in release.get("assets") or []:
        name, url = str(asset.get("name", "")), str(asset.get("browser_download_url", ""))
        if name and fetch.trusted(url):
            found[name] = url
    return found


def bare(tag: str) -> str:
    return tag.removeprefix("assistant-").removeprefix("v")


def candidates(releases: object) -> list[Candidate]:
    found = []
    for release in releases if isinstance(releases, list) else []:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", ""))
        assets = _assets(release)
        if not tag.startswith(("v", "assistant-v")) or not assets.get("manifest.json"):
            continue
        try:
            manifest.version_key(bare(tag))
        except manifest.UpdateRejected:
            log.warning("Release con versione non valida ignorata: %s", tag)
            continue
        found.append(Candidate(bare(tag), tag, assets))
    return sorted(found, key=lambda item: manifest.version_key(item.version))


def choose(found: list[Candidate], current: str) -> Candidate | None:
    newer = [item for item in found if manifest.newer(item.version, current)]
    if not newer:
        return None
    signed = [item for item in newer if item.signed]
    if signed:
        if not newer[-1].signed:
            log.warning("Release %s senza firma: installo l'ultima firmata %s", newer[-1].tag, signed[-1].tag)
        return signed[-1]
    raise UpdateFailure("release_unsigned", newer[-1].tag)


def latest(current: str, stop: threading.Event) -> Candidate | None:
    raw = fetch.get(RELEASES, LIST_LIMIT, stop, accept=fetch.JSON)
    try:
        releases = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise UpdateFailure("server_rejected", "release list unreadable") from exc
    return choose(candidates(releases), current)
