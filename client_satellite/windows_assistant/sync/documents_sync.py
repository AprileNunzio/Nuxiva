import base64
import hashlib
import logging
import os
import shutil
import threading
from pathlib import Path

from senses import places

log = logging.getLogger("nuxiva.doc_sync")
SYNC_INTERVAL = 4.0
SKIP_FILES = {".DS_Store", "desktop.ini", "Thumbs.db"}


def _is_temp_file(name: str) -> bool:
    return name.startswith("~") or name.startswith(".~") or name.endswith(".tmp") or name.endswith(".crdownload")


def documents_dir() -> Path:
    try:
        guid = places.KNOWN_FOLDERS.get("Documenti", "")
        known = places.known_folder(guid) if guid else ""
        if known and os.path.isdir(known):
            return Path(known)
    except Exception:
        pass
    home = Path.home()
    for candidate in ("Documents", "Documenti"):
        cand_path = home / candidate
        if cand_path.is_dir():
            return cand_path
    return home / "Documents"


def nuxiva_folder() -> Path:
    folder = documents_dir() / "Nuxiva"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Impossibile creare cartella Nuxiva nei Documenti: %s", exc)
    return folder


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class DocumentsSync(threading.Thread):
    def __init__(self, client, cfg: dict, notify) -> None:
        super().__init__(daemon=True, name="documents_sync")
        self.client, self.cfg, self.notify = client, cfg, notify
        self.running = threading.Event()
        self.trigger = threading.Event()
        self.local_dir = nuxiva_folder()
        self.person_slug = str(cfg.get("person_slug") or "").strip() or "default"
        self.smb_path = ""
        self.last_sync = 0.0

    def apply_config(self, sync_info: dict) -> None:
        if not isinstance(sync_info, dict):
            return
        slug = str(sync_info.get("person_slug") or "").strip()
        if slug and slug != self.person_slug:
            self.person_slug = slug
            self.cfg["person_slug"] = slug
        self.smb_path = str(sync_info.get("smb_path") or "").strip()
        self.trigger.set()

    def stop(self) -> None:
        self.running.clear()
        self.trigger.set()

    def scan_local(self) -> list[dict]:
        items = []
        if not self.local_dir.is_dir():
            return items
        for root, dirs, files in os.walk(self.local_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and not _is_temp_file(d)]
            for name in files:
                if name.startswith(".") or name in SKIP_FILES or _is_temp_file(name):
                    continue
                file_path = Path(root) / name
                try:
                    stat = file_path.stat()
                    rel = str(file_path.relative_to(self.local_dir)).replace("\\", "/")
                    items.append({
                        "path": rel,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "sha256": _file_sha256(file_path),
                    })
                except OSError:
                    continue
        return items

    def _sync_direct_smb(self, smb_dir: Path) -> int:
        count = 0
        local_files = {f["path"]: f for f in self.scan_local()}
        smb_files = {}
        for root, dirs, files in os.walk(smb_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and not _is_temp_file(d)]
            for name in files:
                if name.startswith(".") or name in SKIP_FILES or _is_temp_file(name) or name == "LEGGIMI.txt":
                    continue
                file_path = Path(root) / name
                try:
                    stat = file_path.stat()
                    rel = str(file_path.relative_to(smb_dir)).replace("\\", "/")
                    smb_files[rel] = {"path": rel, "size": stat.st_size, "mtime": stat.st_mtime, "file": file_path}
                except OSError:
                    continue

        for rel, s_info in smb_files.items():
            l_info = local_files.get(rel)
            if not l_info or s_info["mtime"] > (l_info["mtime"] + 1.0):
                dest = self.local_dir / Path(rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s_info["file"], dest)
                count += 1

        for rel, l_info in local_files.items():
            s_info = smb_files.get(rel)
            if not s_info or l_info["mtime"] > (s_info["mtime"] + 1.0):
                dest = smb_dir / Path(rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.local_dir / Path(rel), dest)
                count += 1

        return count

    def _sync_api(self, local_items: list[dict]) -> int:
        status_resp = self.client.request("/api/nodes/sync/status", {"files": local_items})
        if not isinstance(status_resp, dict):
            return 0
        to_pull = status_resp.get("to_pull") or []
        to_push = status_resp.get("to_push") or []
        count = 0

        for rel in to_pull:
            if not rel or _is_temp_file(rel):
                continue
            pull_resp = self.client.request("/api/nodes/sync/pull", {"path": rel})
            if isinstance(pull_resp, dict) and pull_resp.get("content_b64"):
                data = base64.b64decode(pull_resp["content_b64"])
                dest = self.local_dir / Path(rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp_sync")
                tmp.write_bytes(data)
                os.replace(tmp, dest)
                mtime = pull_resp.get("mtime")
                if isinstance(mtime, (int, float)) and mtime > 0:
                    try:
                        os.utime(dest, (mtime, mtime))
                    except OSError:
                        pass
                count += 1

        for rel in to_push:
            if not rel or _is_temp_file(rel):
                continue
            src = self.local_dir / Path(rel)
            if not src.is_file():
                continue
            data = src.read_bytes()
            b64_content = base64.b64encode(data).decode("ascii")
            mtime = src.stat().st_mtime
            self.client.request("/api/nodes/sync/push", {"path": rel, "content_b64": b64_content, "mtime": mtime})
            count += 1

        return count

    def cycle(self) -> None:
        try:
            self.local_dir = nuxiva_folder()
            if self.smb_path and os.path.exists(self.smb_path):
                synced = self._sync_direct_smb(Path(self.smb_path))
            else:
                local_items = self.scan_local()
                synced = self._sync_api(local_items)
            if synced > 0:
                self.notify(f"📁 Nuxiva: {synced} file sincronizzati")
        except Exception as exc:
            log.debug("Errore ciclo sincronizzazione Documenti: %s", exc)

    def run(self) -> None:
        self.running.set()
        log.info("Sincronizzazione Documenti Nuxiva avviata su %s", self.local_dir)
        while self.running.is_set():
            self.trigger.wait(timeout=SYNC_INTERVAL)
            self.trigger.clear()
            if not self.running.is_set():
                break
            self.cycle()
