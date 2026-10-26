import json
import logging
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

DEMO: bool = False

from config import ETC_DIR, LOG_DIR, STATE_DIR
from features.factory_reset import catalog, engine
from state import store

log = logging.getLogger("nuxiva.factory_reset")
UNIT = "nuxiva-factory-reset"
ENGINE = Path(engine.__file__).resolve()
REPLY_GRACE = 4
REPORT = STATE_DIR / "factory_reset.json"


class ResetError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def share_roots(include: bool) -> list[Path]:
    if not include:
        return []
    return [Path(item) for item in catalog.SHARE_ROOTS if Path(item).is_dir() and not Path(item).is_symlink()]


def keep_state(keep_backups: bool) -> frozenset[str]:
    return frozenset({"backups"}) if keep_backups else frozenset()


def inventory(keep_backups: bool = False, include_shares: bool = False) -> dict:
    kept = keep_state(keep_backups)
    state = engine.scan(STATE_DIR, kept)
    logs = engine.scan(LOG_DIR)
    etc = [row for row in engine.scan(ETC_DIR) if row["name"] not in catalog.KEEP_ETC or row["name"] == "nuxiva.env"]
    shares = [row for root in share_roots(include_shares) for row in engine.scan(root)]
    domains = catalog.group(state, logs, etc)
    if shares:
        domains.append({"id": "shares", "items": len(shares), "files": sum(r["files"] for r in shares),
                        "bytes": sum(r["bytes"] for r in shares)})
    return {"domains": domains, "files": sum(d["files"] for d in domains), "bytes": sum(d["bytes"] for d in domains),
            "kept": sorted(kept)}


def blockers() -> list[str]:
    found = []
    try:
        from orchestrator import orch
        if orch.busy:
            found.append("system_busy")
    except ImportError:
        pass
    return found


def last_report() -> dict | None:
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def build_plan(user: str, keep_backups: bool, include_shares: bool) -> dict:
    return {
        "id": secrets.token_hex(6), "by": str(user)[:64], "state": str(STATE_DIR), "etc": str(ETC_DIR), "log": str(LOG_DIR),
        "extra": [str(path) for path in share_roots(include_shares)], "keep_state": sorted(keep_state(keep_backups)),
        "keep_etc": sorted(catalog.KEEP_ETC), "keep_env": sorted(catalog.KEEP_ENV), "rotate_env": sorted(catalog.ROTATE_ENV),
        "services": [] if (DEMO or os.environ.get("NUXIVA_TEST_AUTH") == "1") else list(catalog.SERVICES), "delay": REPLY_GRACE,
    }


def write_plan(plan: dict) -> Path:
    base = Path("/run") if Path("/run").is_dir() and os.access("/run", os.W_OK) else Path(tempfile.gettempdir())
    folder = Path(tempfile.mkdtemp(prefix="nuxiva-reset-", dir=base))
    os.chmod(folder, 0o700)
    target = folder / "plan.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(plan, handle)
    return target


def detach(plan_file: Path) -> None:
    command = [sys.executable, "-I", str(ENGINE), str(plan_file)]
    if shutil.which("systemd-run"):
        command = ["systemd-run", "--quiet", "--collect", f"--unit={UNIT}", *command]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=30)
        except subprocess.CalledProcessError as exc:
            raise ResetError("reset_running", 409) from exc
        return
    subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_demo(plan_file: Path) -> None:
    plan = engine.load_plan(plan_file)
    plan_file.unlink(missing_ok=True)
    threading.Thread(target=engine.execute, args=(plan,), daemon=True, name="factory-reset-demo").start()


def start(user: str, keep_backups: bool, include_shares: bool) -> dict:
    blocked = blockers()
    if blocked:
        raise ResetError(blocked[0], 409)
    plan = build_plan(user, keep_backups, include_shares)
    plan_file = write_plan(plan)
    store.event("WARN", f"Ripristino di fabbrica avviato da {user}", "factory_reset")
    log.warning("factory reset started by %s (plan %s)", user, plan["id"])
    if DEMO:
        run_demo(plan_file)
    else:
        detach(plan_file)
    return {"id": plan["id"], "status": "started"}
