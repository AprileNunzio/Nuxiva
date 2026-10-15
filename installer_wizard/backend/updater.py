import asyncio
import json
import re
import time

import httpx

from config import DEMO, NUXIVA_DIR, STATE_DIR, env_get
from health import sh
from state import now_iso, store

PENDING_FILE = STATE_DIR / "update_pending.json"
BAD_REVS_FILE = STATE_DIR / "bad_revs"
LAST_GOOD_FILE = STATE_DIR / "last_good_rev"
GATED_JOBS = {"validate-python", "tests", "kernel-tests", "native-core", "validate-scripts", "validate-web-client"}
UNREACHABLE_GRACE = 3600
BAD_REVS_COOLDOWN = 1800.0
PRIORITY_FETCH_TIMEOUT = 45
_ci: dict[str, tuple[str, float]] = {}
_unreachable_since = 0.0


async def git(*args: str, timeout: float = 120) -> tuple[int, str]:
    return await sh("git", "-c", "safe.directory=*", "-C", str(NUXIVA_DIR), *args, timeout=timeout)


def _bad_revs_map() -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        for line in BAD_REVS_FILE.read_text().splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            sha = parts[0]
            ts = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "", 1).isdigit() else 0.0
            out[sha] = max(out.get(sha, 0.0), ts)
    except OSError:
        pass
    return out


def _bad_revs(cooldown: float = BAD_REVS_COOLDOWN) -> set:
    now = time.time()
    res = set()
    for sha, ts in _bad_revs_map().items():
        if ts == 0.0 or (now - ts) < cooldown:
            res.add(sha)
    return res


def clear_bad_rev(sha: str | None = None) -> None:
    try:
        if not BAD_REVS_FILE.exists():
            return
        if not sha:
            BAD_REVS_FILE.unlink(missing_ok=True)
            return
        bm = _bad_revs_map()
        bm.pop(sha, None)
        short = sha[:7]
        for k in list(bm.keys()):
            if k.startswith(short) or short.startswith(k):
                bm.pop(k, None)
        lines = [f"{k} {v}" if v > 0 else k for k, v in bm.items()]
        BAD_REVS_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))
    except OSError:
        pass


def mark_bad_rev(sha: str) -> None:
    try:
        bm = _bad_revs_map()
        bm[sha] = time.time()
        lines = [f"{k} {v}" for k, v in bm.items()]
        BAD_REVS_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))
    except OSError:
        pass


def branch() -> str:
    return env_get("NUXIVA_UPDATE_BRANCH", "main") or "main"


async def current_rev() -> str:
    code, out = await git("rev-parse", "HEAD")
    return out if code == 0 else ""


def require_ci() -> bool:
    return env_get("NUXIVA_UPDATE_REQUIRE_CI", "1") != "0"


async def _slug() -> str:
    _, url = await git("remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+/[^/.\s]+?)(?:\.git)?$", url.strip())
    return m.group(1) if m else ""


async def ci_status(sha: str) -> str:
    global _unreachable_since
    cached = _ci.get(sha)
    if cached and (cached[0] == "success" or time.time() - cached[1] < 60):
        return cached[0]
    slug = await _slug()
    if not slug:
        return "unknown"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://api.github.com/repos/{slug}/commits/{sha}/check-runs",
                headers={"Accept": "application/vnd.github+json"},
                params={"per_page": 50},
            )
            r.raise_for_status()
            check_runs = r.json().get("check_runs", [])
            _unreachable_since = 0.0

            runs = [c for c in check_runs if any(j in c.get("name", "") for j in GATED_JOBS)]
            if not runs and check_runs:
                runs = check_runs

            if runs:
                if any(c.get("conclusion") in ("failure", "cancelled", "timed_out", "action_required") for c in runs):
                    status = "failure"
                elif any(c.get("status") in ("in_progress", "queued") or c.get("status") != "completed" for c in runs):
                    status = "pending"
                else:
                    status = "success"
            else:
                rw = await client.get(
                    f"https://api.github.com/repos/{slug}/actions/runs",
                    headers={"Accept": "application/vnd.github+json"},
                    params={"head_sha": sha, "per_page": 10},
                )
                rw.raise_for_status()
                w_runs = rw.json().get("workflow_runs", [])
                if w_runs:
                    if any(w.get("conclusion") in ("failure", "cancelled", "timed_out") for w in w_runs):
                        status = "failure"
                    elif any(w.get("status") in ("queued", "in_progress") for w in w_runs):
                        status = "pending"
                    elif any(w.get("status") == "completed" and w.get("conclusion") == "success" for w in w_runs):
                        status = "success"
                    else:
                        status = "pending"
                else:
                    code, age_str = await git("log", "-1", "--format=%ct", sha)
                    commit_ts = float(age_str.strip()) if code == 0 and age_str.strip().isdigit() else 0.0
                    if commit_ts > 0 and (time.time() - commit_ts) > 600:
                        status = "untested"
                    else:
                        status = "pending"
    except (httpx.HTTPError, ValueError):
        _unreachable_since = _unreachable_since or time.time()
        return "unknown"

    _ci[sha] = (status, time.time())
    return status


async def pick_target(remote: str, allow_bad: bool = False) -> tuple[str, str]:
    if not require_ci():
        return remote, ""
    _, revs = await git("rev-list", "--max-count=30", f"HEAD..{remote}")
    waiting = ""
    bad_set = set() if allow_bad else _bad_revs()
    skipped_bad = ""
    for sha in revs.split():
        if sha in bad_set:
            if not skipped_bad:
                skipped_bad = sha
            continue
        status = await ci_status(sha)
        if status == "success":
            return sha, waiting
        if status == "pending" and not waiting:
            waiting = f"test in corso su GitHub per {sha[:7]}"
        if status == "failure" and not waiting:
            waiting = f"{sha[:7]} non ha superato i test su GitHub: la salto"
        if status == "untested" and not waiting:
            waiting = f"{sha[:7]} non ha test automatici su GitHub"
        if status == "unknown":
            if _unreachable_since and time.time() - _unreachable_since > UNREACHABLE_GRACE:
                return sha, "GitHub non raggiungibile da oltre un'ora: aggiorno senza conferma dei test"
            return "", "GitHub non raggiungibile: attendo la conferma dei test"
    if skipped_bad:
        waiting = f"{skipped_bad[:7]} ripristinata in precedenza (riprova con Aggiorna ora)"
    return "", waiting


async def mark_good() -> None:
    rev = await current_rev()
    if rev:
        store.last_good_rev = rev
        LAST_GOOD_FILE.write_text(rev)
        store.save()


def auto_update_enabled() -> bool:
    return not DEMO and env_get("NUXIVA_AUTO_UPDATE", "1") != "0"


async def check(fetch_timeout: float = 180, allow_bad: bool = False) -> dict:
    info = store.update
    info["last_check"] = now_iso()
    if DEMO:
        info.update(local_rev="demo", remote_rev="demo", available=False, last_result="Modalità demo")
        return info
    code, out = await git("fetch", "--quiet", "origin", branch(), timeout=fetch_timeout)
    if code != 0:
        info["last_result"] = f"Fetch non riuscito: {out[:160]}"
        store.touch()
        return info
    local = await current_rev()
    _, remote = await git("rev-parse", f"origin/{branch()}")
    _, log = await git("log", "--oneline", "-n", "15", f"HEAD..origin/{branch()}")
    target, note = (await pick_target(remote, allow_bad=allow_bad)) if remote and remote != local else ("", "")
    if not target and remote and remote != local and not allow_bad:
        target_override, _ = await pick_target(remote, allow_bad=True)
        if target_override:
            target = target_override
            if not note:
                note = f"{target[:7]} disponibile (precedentemente ripristinato)"
    available = bool(target) and target != local
    info.update(local_rev=local, remote_rev=remote, target_rev=target, ci_note=note,
                available=available,
                changelog=log.splitlines() if log else [])
    if note:
        info["last_result"] = note
    store.touch()
    return info


async def apply(reason: str = "automatico", fetch_timeout: float = 180, force: bool = False) -> bool:
    info = await check(fetch_timeout, allow_bad=force)
    target = info.get("target_rev")
    if not target and force and info.get("remote_rev") and info.get("remote_rev") != info.get("local_rev"):
        target = info["remote_rev"]
    if not target or target == info.get("local_rev"):
        return False
    if not force and target in _bad_revs():
        return False
    if force:
        clear_bad_rev(target)
    previous = pending()
    rollback_to = previous["from"] if previous else info["local_rev"]
    store.event("INFO", f"Aggiornamento {reason}: {info['local_rev'][:7]} → {target[:7]} (test superati)", "updater")
    store.set_phase("UPDATING", "Download del nuovo firmware cognitivo…")
    PENDING_FILE.write_text(json.dumps({"from": rollback_to, "to": target, "at": time.time()}))
    code, out = await git("reset", "--hard", target)
    if code != 0:
        PENDING_FILE.unlink(missing_ok=True)
        store.event("ERROR", f"Aggiornamento non applicato: {out[:200]}", "updater")
        store.set_phase("READY", "Aggiornamento annullato")
        return False
    store.message = "Riavvio del supervisore sulla nuova versione…"
    store.touch()
    await asyncio.sleep(2)
    await sh("systemctl", "restart", "--no-block", "nuxiva-supervisor.service", timeout=10)
    return True


async def priority_update(reason: str) -> bool:
    if not auto_update_enabled():
        return False
    store.message = "Cerco una versione più recente online…"
    store.touch()
    return await apply(reason, PRIORITY_FETCH_TIMEOUT)


def pending() -> dict | None:
    try:
        return json.loads(PENDING_FILE.read_text())
    except (OSError, ValueError):
        return None


async def finish_pending(success: bool) -> bool:
    data = pending()
    if not data:
        return False
    PENDING_FILE.unlink(missing_ok=True)
    if success:
        from datetime import datetime
        local_time = datetime.now().astimezone().strftime('%d/%m/%Y %H:%M:%S')
        store.update["last_result"] = f"Aggiornato a {data['to'][:7]} il {local_time}"
        store.event("INFO", "Aggiornamento verificato e confermato", "updater")
        clear_bad_rev(data["to"])
        await mark_good()
        return False
    store.update["last_result"] = f"Rollback: {data['to'][:7]} non ha superato la verifica"
    store.event("ERROR", f"Aggiornamento {data['to'][:7]} fallito: rollback a {data['from'][:7]}", "updater")
    mark_bad_rev(data["to"])
    await git("reset", "--hard", data["from"])
    await sh("systemctl", "restart", "--no-block", "nuxiva-supervisor.service", timeout=10)
    return True


async def _scheduled_cycle(stuck: bool) -> None:
    from datetime import datetime

    from features.update_center.policy import in_window, load_policy

    policy = load_policy(env_get)
    if not policy.auto_update:
        await check()
        return
    if not stuck and not in_window(datetime.now(), policy.window):
        await check()
        return
    applied = await apply("correttivo (sistema bloccato)" if stuck else "automatico")
    if applied and policy.sync_nodes:
        from features.nodes.registry import registry
        from features.update_center.rollout import queue_updates

        queued = queue_updates(registry, [n["id"] for n in registry.listing()])
        store.event("INFO", f"Aggiornamento simultaneo inviato a {len(queued)} nodi", "updater")


async def scheduler() -> None:
    await asyncio.sleep(120)
    while True:
        stuck = store.phase == "ERROR" or getattr(store, "pipeline_failed", False)
        if store.phase != "READY" and not stuck:
            await asyncio.sleep(60)
            continue
        try:
            await _scheduled_cycle(stuck)
        except Exception as exc:
            store.event("ERROR", f"Errore updater: {exc}", "updater")
        try:
            minutes = float(env_get("NUXIVA_UPDATE_INTERVAL_MIN", "5") or 5)
        except ValueError:
            minutes = 5
        await asyncio.sleep(max(1.0, minutes) * 60)
