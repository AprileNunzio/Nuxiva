import json
import os
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path

OVERWRITE_MAX = 8 * 1024 * 1024
BLOCK = 1 << 20
CANARY_LIMIT = 32
RESIDUE_LIMIT = 40
MIN_DEPTH = 3
SENSITIVE_SUFFIXES = (".key", ".db", ".json", ".pem", ".onnx", ".npy", ".clip", ".sqlite")
MARKERS = ("setup.json", "factory_reset.json")
SYSTEMCTL_TIMEOUT = 90


class PlanError(ValueError):
    pass


def check_root(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or len(path.parts) < MIN_DEPTH or ".." in path.parts:
        raise PlanError("unsafe_root")
    if path.is_symlink():
        raise PlanError("symlink_root")
    return path


def entries(root: Path, keep: frozenset[str] = frozenset()) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(child for child in root.iterdir() if child.name not in keep)


def measure(path: Path, device: int) -> tuple[int, int]:
    files = size = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            info = current.lstat()
        except OSError:
            continue
        if stat.S_ISDIR(info.st_mode):
            if info.st_dev != device:
                continue
            try:
                stack.extend(current.iterdir())
            except OSError:
                continue
        else:
            files += 1
            size += info.st_size
    return files, size


def scan(root: Path, keep: frozenset[str] = frozenset()) -> list[dict]:
    if not root.is_dir():
        return []
    device = root.lstat().st_dev
    rows = []
    for child in entries(root, keep):
        files, size = measure(child, device)
        rows.append({"name": child.name, "files": files, "bytes": size})
    return rows


def shred(path: Path, info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_size == 0 or info.st_size > OVERWRITE_MAX:
        return
    try:
        fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
    except OSError:
        return
    with os.fdopen(fd, "r+b", buffering=0) as handle:
        remaining = info.st_size
        while remaining > 0:
            step = min(BLOCK, remaining)
            handle.write(bytes(step))
            remaining -= step
        os.fsync(handle.fileno())


def erase(path: Path, device: int, counters: dict) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        if info.st_dev != device:
            counters["skipped_mounts"] += 1
            return
        for child in list(path.iterdir()):
            erase(child, device, counters)
        try:
            path.rmdir()
        except OSError:
            counters["failed"] += 1
        return
    shred(path, info)
    try:
        path.unlink()
    except OSError:
        counters["failed"] += 1
        return
    counters["files"] += 1
    counters["bytes"] += info.st_size


def wipe_root(root: Path, keep: frozenset[str] = frozenset()) -> dict:
    counters = {"files": 0, "bytes": 0, "failed": 0, "skipped_mounts": 0}
    if not root.is_dir():
        return counters
    device = root.lstat().st_dev
    for child in entries(root, keep):
        erase(child, device, counters)
    return counters


def residue(root: Path, allowed: frozenset[str]) -> list[str]:
    left = []
    if not root.is_dir():
        return left
    device = root.lstat().st_dev
    for child in entries(root, allowed):
        try:
            info = child.lstat()
        except OSError:
            continue
        if stat.S_ISDIR(info.st_mode) and info.st_dev != device:
            continue
        left.append(child.name)
        if len(left) >= RESIDUE_LIMIT:
            break
    return left


def canaries(root: Path, keep: frozenset[str]) -> list[str]:
    found = []
    device = root.lstat().st_dev if root.is_dir() else 0
    for top in entries(root, keep):
        stack = [top]
        while stack and len(found) < CANARY_LIMIT:
            current = stack.pop()
            try:
                info = current.lstat()
            except OSError:
                continue
            if stat.S_ISDIR(info.st_mode):
                if info.st_dev == device:
                    try:
                        stack.extend(sorted(current.iterdir()))
                    except OSError:
                        pass
            elif stat.S_ISREG(info.st_mode) and current.name.endswith(SENSITIVE_SUFFIXES):
                found.append(str(current))
    return found


def open_deleted(roots: list[Path]) -> int:
    proc = Path("/proc")
    if not proc.is_dir():
        return 0
    prefixes = tuple(str(root) for root in roots)
    count = 0
    for process in proc.iterdir():
        if not process.name.isdigit() or process.name == str(os.getpid()):
            continue
        try:
            handles = list((process / "fd").iterdir())
        except OSError:
            continue
        for handle in handles:
            try:
                target = os.readlink(handle)
            except OSError:
                continue
            if target.endswith(" (deleted)") and target.startswith(prefixes):
                count += 1
    return count


def parse_env(text: str) -> list[tuple[str, str]]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        rows.append((key.strip(), value))
    return rows


def write_private(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def reset_env(path: Path, keep: frozenset[str], rotate: frozenset[str]) -> dict:
    summary = {"kept": 0, "rotated": 0, "removed": 0}
    if not path.is_file():
        return summary
    kept = []
    seen = set()
    for key, value in parse_env(path.read_text(encoding="utf-8", errors="replace")):
        if key in rotate:
            kept.append(f"{key}={secrets.token_hex(32)}")
            seen.add(key)
            summary["rotated"] += 1
        elif key in keep:
            kept.append(f"{key}={value}")
            summary["kept"] += 1
        else:
            summary["removed"] += 1
    for key in sorted(rotate - seen):
        kept.append(f"{key}={secrets.token_hex(32)}")
        summary["rotated"] += 1
    shred(path, path.lstat())
    write_private(path, ("\n".join(kept) + "\n" if kept else "").encode())
    return summary


def systemctl(*arguments: str) -> bool:
    try:
        done = subprocess.run(["systemctl", *arguments], capture_output=True, timeout=SYSTEMCTL_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def active(unit: str) -> bool:
    return systemctl("is-active", "--quiet", unit)


def stop_services(units: list[str]) -> dict:
    was_active = [unit for unit in units if active(unit)]
    failed = [unit for unit in was_active if not systemctl("stop", unit)]
    return {"active": was_active, "failed": failed}


def start_services(units: list[str]) -> list[str]:
    return [unit for unit in units if not systemctl("start", unit)]


def write_markers(state: Path, by: str, report: dict) -> None:
    state.mkdir(parents=True, exist_ok=True)
    write_private(state / "setup.json", json.dumps({"done": False, "reopened_at": time.time(), "by": by}).encode())
    write_private(state / "factory_reset.json", json.dumps(report, ensure_ascii=False).encode())


def execute(plan: dict) -> dict:
    state = check_root(plan["state"])
    etc = check_root(plan["etc"])
    log = check_root(plan["log"])
    extra = [check_root(item) for item in plan.get("extra", [])]
    keep_state = frozenset(plan.get("keep_state", []))
    keep_etc = frozenset(plan.get("keep_etc", []))
    time.sleep(float(plan.get("delay", 0)))
    started = time.time()
    services = stop_services(plan.get("services", [])) if plan.get("services") else {"active": [], "failed": []}
    marks = canaries(state, keep_state)
    roots = [("state", state, keep_state), ("etc", etc, keep_etc), ("logs", log, frozenset())]
    roots += [(f"extra{index}", path, frozenset()) for index, path in enumerate(extra)]
    results = []
    for name, root, keep in roots:
        counters = wipe_root(root, keep)
        results.append({"name": name, **counters})
    env = reset_env(etc / "nuxiva.env", frozenset(plan.get("keep_env", [])), frozenset(plan.get("rotate_env", [])))
    leftovers = {}
    for name, root, keep in roots:
        allowed = keep | (frozenset(MARKERS) if name == "state" else frozenset())
        left = residue(root, allowed)
        if left:
            leftovers[name] = left
    survivors = [item for item in marks if os.path.lexists(item)]
    deleted_open = open_deleted([root for _, root, _ in roots])
    clean = not leftovers and not survivors and not any(item["failed"] for item in results)
    report = {
        "id": plan.get("id", ""), "by": plan.get("by", ""), "started": started, "finished": time.time(),
        "status": "verified" if clean else "incomplete", "roots": results, "env": env,
        "canaries": {"checked": len(marks), "survivors": len(survivors)}, "leftovers": leftovers,
        "open_deleted": deleted_open, "kept": sorted(keep_state), "services": services,
        "skipped_mounts": sum(item["skipped_mounts"] for item in results),
    }
    write_markers(state, plan.get("by", ""), report)
    report["services"]["not_started"] = start_services(list(reversed(services["active"])))
    write_markers(state, plan.get("by", ""), report)
    return report


def load_plan(path: Path) -> dict:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PlanError("untrusted_plan")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise PlanError("invalid_plan")
    return plan


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 2
    plan_path = Path(argv[1])
    plan = load_plan(plan_path)
    shred(plan_path, plan_path.lstat())
    plan_path.unlink(missing_ok=True)
    return 0 if execute(plan)["status"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
