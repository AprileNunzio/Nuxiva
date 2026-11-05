from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import nuxiva_native as _native
except ImportError:
    _native = None

_REQUIRED = ("update_signature", "update_verify_tree", "update_impact", "update_changelog", "update_pipeline_advance", "update_valid_rev")
RUST = _native is not None and all(hasattr(_native, name) for name in _REQUIRED)
ENGINE = "rust" if RUST else "python"
ENGINE_VERSION = str(getattr(_native, "__version__", "")) if RUST else ""

STAGES = (("check", 5), ("fetch", 15), ("verify_ci", 10), ("verify_signature", 10), ("snapshot", 5),
          ("apply", 20), ("integrity", 15), ("restart", 10), ("confirm", 10))
STATUSES = {"running", "done", "skipped", "failed"}
_REV = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
MAX_LISTED = 40


def valid_rev(rev: str) -> bool:
    if RUST:
        return bool(_native.update_valid_rev(rev))
    return bool(_REV.match(rev.strip()))


def _clean(value: str) -> Optional[str]:
    text = _CONTROL.sub("", value)[:160].strip()
    return text or None


def _py_signature(raw: str, code: int) -> Dict[str, Any]:
    flags: Dict[str, bool] = {}
    fingerprint = signer = None
    gpg = False
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("[GNUPG:] "):
            continue
        gpg = True
        parts = line[9:].split(" ", 2) + ["", ""]
        keyword, first, tail = parts[0], parts[1], parts[2]
        flags[keyword] = True
        if keyword == "GOODSIG":
            signer = _clean(tail)
        elif keyword == "VALIDSIG":
            fingerprint = _clean(first)
    fmt = "openpgp" if gpg else "none"
    if gpg:
        if flags.get("BADSIG"):
            verdict = "bad"
        elif flags.get("REVKEYSIG"):
            verdict = "revoked"
        elif flags.get("EXPSIG") or flags.get("EXPKEYSIG"):
            verdict = "expired"
        elif flags.get("GOODSIG"):
            verdict = "trusted" if flags.get("TRUST_ULTIMATE") or flags.get("TRUST_FULLY") else "valid"
        elif flags.get("NO_PUBKEY") or flags.get("ERRSIG"):
            verdict = "unknown_key"
        else:
            verdict = "unsigned"
    else:
        verdict = "unsigned"
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith('Good "git" signature for '):
                fmt, verdict = "ssh", "valid"
                who, _, key = line[len('Good "git" signature for '):].partition(" with ")
                signer, fingerprint = _clean(who), _clean(key.split()[-1]) if key.split() else None
                break
            if line.startswith("Could not verify signature") or "Signature verification failed" in line:
                fmt, verdict = "ssh", "bad"
                break
            if "No principal matched" in line or "allowedSignersFile needs to be configured" in line:
                fmt, verdict = "ssh", "unknown_key"
                break
    if code != 0 and verdict in ("trusted", "valid"):
        verdict = "bad"
    return {"verdict": verdict, "blocking": verdict in ("bad", "revoked"), "format": fmt,
            "fingerprint": fingerprint, "signer": signer}


def signature(raw: str, code: int) -> Dict[str, Any]:
    if RUST:
        return json.loads(_native.update_signature(raw, int(code)))
    return _py_signature(raw, int(code))


def _py_entries(raw: str) -> List[Dict[str, str]]:
    out = []
    for record in raw.split("\0"):
        meta, sep, path = record.partition("\t")
        fields = meta.split(" ")
        if not sep or len(fields) != 3 or not path:
            continue
        mode, kind, oid = fields
        if kind in ("blob", "commit") and _OID.match(oid):
            out.append({"mode": mode, "oid": oid, "path": path})
    return out


def _py_actual(path: Path, mode: str, long: bool) -> str:
    algo = hashlib.sha256 if long else hashlib.sha1
    meta = path.lstat()
    if mode == "120000":
        if not stat.S_ISLNK(meta.st_mode):
            raise ValueError("expected_symlink")
        data = os.fsencode(os.readlink(path))
        return algo(b"blob %d\0" % len(data) + data).hexdigest()
    if not stat.S_ISREG(meta.st_mode):
        raise ValueError("expected_file")
    size = meta.st_size
    digest = algo(b"blob %d\0" % size)
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _py_verify(root: str, raw: str) -> Dict[str, Any]:
    entries = sorted(_py_entries(raw), key=lambda e: e["path"])
    long = bool(entries) and len(entries[0]["oid"]) == 64
    report: Dict[str, Any] = {"algorithm": "sha256" if long else "sha1", "checked": 0, "matched": 0, "skipped": 0,
                              "mismatched": [], "missing": [], "rejected": [], "fingerprint": "", "intact": False}
    base = Path(root).resolve()
    fingerprint = hashlib.sha256()
    failures = 0

    def flag(bucket: str, value: str) -> None:
        if len(report[bucket]) < MAX_LISTED:
            report[bucket].append(value)

    for entry in entries:
        fingerprint.update(f"{entry['mode']} {entry['oid']} {entry['path']}\n".encode())
        if entry["mode"] == "160000":
            report["skipped"] += 1
            continue
        report["checked"] += 1
        rel = Path(entry["path"])
        if (len(entry["oid"]) == 64) != long or rel.is_absolute() or any(p in ("..", ".", "") for p in rel.parts):
            failures += 1
            flag("rejected", entry["path"])
            continue
        target = base / rel
        if not target.parent.resolve().is_relative_to(base):
            failures += 1
            flag("rejected", entry["path"])
            continue
        try:
            actual = _py_actual(target, entry["mode"], long)
        except FileNotFoundError:
            failures += 1
            flag("missing", entry["path"])
            continue
        except (OSError, ValueError):
            failures += 1
            flag("mismatched", entry["path"])
            continue
        if actual == entry["oid"]:
            report["matched"] += 1
        else:
            failures += 1
            flag("mismatched", entry["path"])
    report["fingerprint"] = fingerprint.hexdigest()
    report["intact"] = failures == 0
    return report


def verify_tree(root: str, ls_tree_z: str) -> Dict[str, Any]:
    if RUST:
        return json.loads(_native.update_verify_tree(root, ls_tree_z))
    return _py_verify(root, ls_tree_z)


def impact(name_status_z: str) -> Dict[str, Any]:
    if RUST:
        return json.loads(_native.update_impact(name_status_z))
    tokens = [t for t in name_status_z.split("\0") if t]
    return {"files": sum(1 for t in tokens if t[:1] in "AMDRCTU" and len(t) <= 4), "components": [], "effects": []}


def changelog(log: str) -> List[Dict[str, Any]]:
    if RUST:
        return json.loads(_native.update_changelog(log))
    out = []
    for line in log.splitlines()[:200]:
        sha, _, subject = line.strip().partition(" ")
        if 7 <= len(sha) <= 64 and all(c in "0123456789abcdefABCDEF" for c in sha) and subject:
            out.append({"sha": sha.lower(), "kind": "other", "scope": None, "breaking": False,
                        "summary": _CONTROL.sub("", subject.split(" / ")[0])[:240].strip()})
    return out


def _py_advance(state: Optional[Dict[str, Any]], stage: str, status: str, now: float) -> Dict[str, Any]:
    pipe = state or {"stages": [{"id": i, "weight": w, "status": "pending", "started_at": None, "finished_at": None}
                                for i, w in STAGES], "percent": 0, "active": None, "outcome": None}
    ids = [s["id"] for s in pipe["stages"]]
    if pipe.get("outcome"):
        raise ValueError("pipeline_terminal")
    if stage not in ids:
        raise ValueError("unknown_stage")
    at = ids.index(stage)
    if any(s["status"] != "pending" for s in pipe["stages"][at + 1:]):
        raise ValueError("stage_regression")
    current = pipe["stages"][at]["status"]
    if not (current == "pending" or (current == "running" and status != "running")):
        raise ValueError("invalid_transition")
    for earlier in pipe["stages"][:at]:
        if earlier["status"] in ("pending", "running"):
            earlier["status"] = "skipped" if earlier["status"] == "pending" else "done"
            earlier["finished_at"] = now
    node = pipe["stages"][at]
    node["started_at"] = node["started_at"] or now
    if status != "running":
        node["finished_at"] = now
    node["status"] = status
    total = sum(s["weight"] for s in pipe["stages"]) or 1
    earned = sum(s["weight"] * (2 if s["status"] in ("done", "skipped") else 1 if s["status"] == "running" else 0)
                 for s in pipe["stages"])
    pipe["percent"] = min(100, earned * 50 // total)
    pipe["active"] = next((s["id"] for s in pipe["stages"] if s["status"] == "running"), None)
    if any(s["status"] == "failed" for s in pipe["stages"]):
        pipe["outcome"] = "failed"
    elif all(s["status"] in ("done", "skipped") for s in pipe["stages"]):
        pipe["outcome"] = "success"
    return pipe


def pipeline_advance(state: Optional[Dict[str, Any]], stage: str, status: str, now: float) -> Dict[str, Any]:
    if status not in STATUSES:
        raise ValueError("invalid stage status")
    if RUST:
        return json.loads(_native.update_pipeline_advance(json.dumps(state) if state else None, stage, status, now))
    return _py_advance(json.loads(json.dumps(state)) if state else None, stage, status, now)

