import hashlib
import json
import logging
import shutil
import tempfile
import threading
import time
from pathlib import Path

from i18n.strings import t
from settings import paths
from updates import fetch, launcher, manifest, releases
from updates.errors import UpdateCancelled, UpdateFailure

log = logging.getLogger("nuxiva.updates")
CHECK_EVERY = 6 * 3600
FIRST_CHECK = 300
RETRY_DELAYS = (300, 900, 3600, 3 * 3600)
NOTIFY_AFTER = 3
SECURITY_CODES = frozenset({"invalid_signature", "hash_mismatch"})
UPDATES_DIR = paths.DATA_DIR / "updates"
STATE_FILE = UPDATES_DIR / "state.json"
WORK_PREFIX = "nuxiva-update-"
MANIFEST_LIMIT = 65536
SIGNATURE_LIMIT = 4096
HASH_CHUNK = 1 << 20


def read_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def prune(root: Path) -> None:
    for entry in root.glob(f"{WORK_PREFIX}*"):
        try:
            shutil.rmtree(entry)
        except OSError as exc:
            log.warning("Cartella di aggiornamento non rimossa %s: %s", entry, exc)


def file_digest(path: Path) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    try:
        with open(path, "rb") as handle:
            while chunk := handle.read(HASH_CHUNK):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise UpdateFailure("storage_failed", exc.strerror or type(exc).__name__) from exc
    return size, digest.hexdigest()


class Updater(threading.Thread):
    def __init__(self, notify, after_launch, translate=t) -> None:
        super().__init__(daemon=True, name="updates")
        self.notify, self.after_launch, self.t = notify, after_launch, translate
        self.wake = threading.Event()
        self.stop_flag = threading.Event()
        self.failures = 0
        self.info = read_state()
        if self.info.get("target") == paths.VERSION:
            self.mark(state="idle", target=None, last_success=int(time.time()), last_error=None)
        elif self.info.get("state") in ("checking", "downloading", "installing"):
            self.mark(state="idle")

    def mark(self, **changes) -> None:
        self.info.update(changes)
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(self.info), encoding="utf-8")
        except OSError as exc:
            log.error("Stato degli aggiornamenti non salvato: %s", exc)

    def fail(self, failure: UpdateFailure) -> None:
        self.failures += 1
        error = {"code": failure.code, "at": int(time.time())}
        if failure.detail:
            error["detail"] = failure.detail
        self.mark(state="failed", target=None, last_error=error)
        log.error("Aggiornamento non riuscito [%s] %s (tentativo %d)", failure.code, failure.detail, self.failures)
        reason = self.t(f"updates.error.{failure.code}")
        detail = failure.detail or failure.code
        if failure.code in SECURITY_CODES:
            self.notify(self.t("updates.rejected", reason=reason, detail=detail))
        elif self.failures == NOTIFY_AFTER:
            self.notify(self.t("updates.failed", reason=reason, detail=detail))

    def report(self) -> dict:
        keys = ("last_check", "last_success", "last_error", "target")
        return {"channel": "windows", "version": paths.VERSION, "state": self.info.get("state", "idle"),
                **{key: self.info[key] for key in keys if self.info.get(key)}}

    def check_now(self) -> None:
        self.wake.set()

    def delay(self) -> int:
        if not self.failures:
            return CHECK_EVERY
        return RETRY_DELAYS[min(self.failures, len(RETRY_DELAYS)) - 1]

    def run(self) -> None:
        if not paths.FROZEN:
            log.info("Aggiornamenti automatici attivi solo nella versione installata")
            return
        prune(UPDATES_DIR)
        self.wake.wait(FIRST_CHECK)
        while not self.stop_flag.is_set():
            self.wake.clear()
            try:
                self.cycle()
                self.failures = 0
            except UpdateCancelled:
                return
            except UpdateFailure as failure:
                self.fail(failure)
            self.wake.wait(self.delay())

    def cycle(self) -> None:
        self.mark(state="checking", last_check=int(time.time()))
        found = releases.latest(paths.VERSION, self.stop_flag)
        if found is None:
            self.mark(state="idle", target=None, last_error=None)
            return
        self.mark(state="downloading", target=found.version)
        release = self.verified(found)
        work = self.workspace()
        try:
            installer = work / f"Nuxiva_Setup_{release.version}.exe"
            digest = fetch.download(release.url, installer, release.size, self.stop_flag)
            manifest.check_digest(release.size, digest, release)
            manifest.check_digest(*file_digest(installer), release)
            if self.stop_flag.is_set():
                raise UpdateCancelled()
            log.info("Aggiornamento %s verificato (firma Ed25519 e SHA-256): installazione", release.version)
            self.mark(state="installing", target=release.version, last_error=None)
            self.notify(self.t("updates.installing", version=release.version))
            launcher.launch(installer)
        except (UpdateFailure, UpdateCancelled):
            prune(UPDATES_DIR)
            raise
        self.after_launch()

    def verified(self, found: releases.Candidate) -> manifest.Release:
        body = fetch.get(found.assets["manifest.json"], MANIFEST_LIMIT, self.stop_flag)
        signature = fetch.get(found.assets["manifest.sig"], SIGNATURE_LIMIT, self.stop_flag)
        release = manifest.verify(body, signature)
        if release.version != found.version:
            raise manifest.UpdateRejected("la versione firmata non corrisponde alla release")
        return release

    @staticmethod
    def workspace() -> Path:
        try:
            UPDATES_DIR.mkdir(parents=True, exist_ok=True)
            return Path(tempfile.mkdtemp(prefix=WORK_PREFIX, dir=UPDATES_DIR))
        except OSError as exc:
            raise UpdateFailure("storage_failed", exc.strerror or type(exc).__name__) from exc

    def stop(self) -> None:
        self.stop_flag.set()
        self.wake.set()
