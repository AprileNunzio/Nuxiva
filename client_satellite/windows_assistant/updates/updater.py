import json
import logging
import subprocess
import threading
import time
import urllib.error
import urllib.request

from settings import paths
from updates import manifest

log = logging.getLogger("nuxiva.updates")
RELEASES = f"https://api.github.com/repos/{manifest.REPOSITORY}/releases?per_page=20"
CHECK_EVERY = 6 * 3600
FIRST_CHECK = 300
TIMEOUT = 30
STATE_FILE = paths.DATA_DIR / "updates" / "state.json"
SILENT = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"]


def _get(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "NUXIVA-Assistente", "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise manifest.UpdateRejected(f"risposta troppo grande da {url}")
    return data


def _assets(release: dict) -> dict[str, str]:
    return {a.get("name", ""): a.get("browser_download_url", "") for a in release.get("assets") or []}


def latest() -> tuple[str, dict[str, str]] | None:
    releases = json.loads(_get(RELEASES, 2_000_000).decode("utf-8"))
    candidates = []
    for release in releases if isinstance(releases, list) else []:
        tag = str(release.get("tag_name", ""))
        assets = _assets(release)
        if (tag.startswith("assistant-v") and not release.get("draft") and not release.get("prerelease")
                and assets.get("manifest.json") and assets.get("manifest.sig")):
            try:
                candidates.append((manifest.version_key(tag.removeprefix("assistant-v")), tag, assets))
            except manifest.UpdateRejected:
                log.warning("Release con versione non valida ignorata: %s", tag)
    if not candidates:
        return None
    _key, tag, assets = max(candidates, key=lambda candidate: candidate[0])
    return tag.removeprefix("assistant-v"), assets


def read_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


class Updater(threading.Thread):
    def __init__(self, notify, after_launch) -> None:
        super().__init__(daemon=True, name="updates")
        self.notify, self.after_launch = notify, after_launch
        self.wake = threading.Event()
        self.stop_flag = threading.Event()
        self.info = read_state()
        if self.info.get("target") == paths.VERSION:
            self.mark(state="idle", target=None, last_success=int(time.time()), last_error=None)
        elif self.info.get("state") in ("checking", "downloading", "installing"):
            self.mark(state="idle")

    def mark(self, **changes) -> None:
        self.info.update(changes)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.info), encoding="utf-8")

    def fail(self, code: str) -> None:
        self.mark(state="failed", target=None, last_error={"code": code, "at": int(time.time())})

    def report(self) -> dict:
        keys = ("last_check", "last_success", "last_error", "target")
        return {"channel": "windows", "version": paths.VERSION, "state": self.info.get("state", "idle"),
                **{key: self.info[key] for key in keys if self.info.get(key)}}

    def check_now(self) -> None:
        self.wake.set()

    def run(self) -> None:
        if not paths.FROZEN:
            log.info("Aggiornamenti automatici attivi solo nella versione installata")
            return
        self.wake.wait(FIRST_CHECK)
        while not self.stop_flag.is_set():
            self.wake.clear()
            try:
                self.cycle()
            except manifest.UpdateRejected as exc:
                self.fail("invalid_signature")
                log.error("Aggiornamento rifiutato: %s", exc)
                self.notify(f"🛑 Aggiornamento rifiutato per sicurezza: {exc}")
            except (urllib.error.URLError, OSError, ValueError) as exc:
                self.mark(state="idle", last_error={"code": "download_failed", "at": int(time.time())})
                log.info("Controllo aggiornamenti non riuscito: %s", exc)
            self.wake.wait(CHECK_EVERY)

    def cycle(self) -> None:
        self.mark(state="checking", last_check=int(time.time()))
        found = latest()
        if not found or not manifest.newer(found[0], paths.VERSION):
            self.mark(state="idle", last_check=int(time.time()), last_error=None)
            return
        version, assets = found
        self.mark(state="downloading", target=version)
        release = manifest.verify(_get(assets["manifest.json"], 65536), _get(assets["manifest.sig"], 4096))
        if release.version != version:
            raise manifest.UpdateRejected("la versione firmata non corrisponde alla release")
        installer = _get(release.url, release.size)
        try:
            manifest.check_file(installer, release)
        except manifest.UpdateRejected:
            self.fail("hash_mismatch")
            raise
        if self.stop_flag.is_set():
            return
        target = paths.DATA_DIR / "updates" / f"Nuxiva_Setup_{release.version}.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(installer)
        log.info("Aggiornamento %s verificato (firma e SHA-256): installazione", release.version)
        self.mark(state="installing", target=release.version)
        self.notify(f"⬆ Aggiornamento {release.version} verificato: installo e riavvio NUXIVA…")
        subprocess.Popen([str(target), *SILENT], close_fds=True)
        self.after_launch()

    def stop(self) -> None:
        self.stop_flag.set()
        self.wake.set()
