from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Tuple

from features.update_center import native
from features.update_center.progress import UpdateProgress

Git = Callable[..., Awaitable[Tuple[int, str]]]

SIGNATURE_TIMEOUT = 30
TREE_TIMEOUT = 90


async def signature(git: Git, target: str) -> Dict[str, Any]:
    code, out = await git("verify-commit", "--raw", "--end-of-options", target, timeout=SIGNATURE_TIMEOUT)
    return native.signature(out, code)


async def impact(git: Git, base: str, target: str) -> Dict[str, Any]:
    code, out = await git("diff", "--name-status", "-z", "--end-of-options", base, target, timeout=TREE_TIMEOUT)
    if code != 0:
        return {"files": 0, "components": [], "effects": [], "error": "diff_unavailable"}
    return native.impact(out)


async def integrity(git: Git, root: Path, target: str) -> Dict[str, Any]:
    code, out = await git("ls-tree", "-r", "-z", "--full-tree", "--end-of-options", target, timeout=TREE_TIMEOUT)
    if code != 0:
        return {"algorithm": "", "checked": 0, "matched": 0, "skipped": 0, "mismatched": [], "missing": [],
                "rejected": ["ls-tree"], "fingerprint": "", "intact": False}
    return native.verify_tree(str(root), out)


async def preflight(git: Git, tracker: UpdateProgress, base: str, target: str, ci_gated: bool) -> bool:
    tracker.step("check", "done")
    tracker.step("fetch", "done", target=target[:7])
    tracker.step("verify_ci", "done" if ci_gated else "skipped")
    tracker.step("verify_signature", "running")
    report = await signature(git, target)
    tracker.attach("signature", report)
    if report["blocking"]:
        tracker.step("verify_signature", "failed", verdict=report["verdict"], fingerprint=report.get("fingerprint"))
        return False
    tone = "ok" if report["verdict"] in ("trusted", "valid") else "warn"
    tracker.step("verify_signature", "done", tone, verdict=report["verdict"], fingerprint=report.get("fingerprint"))
    tracker.attach("impact", await impact(git, base, target))
    return True


async def postflight(git: Git, tracker: UpdateProgress, root: Path, target: str) -> bool:
    tracker.step("integrity", "running")
    report = await integrity(git, root, target)
    if report["checked"] == 0:
        report = {**report, "intact": False, "rejected": [*report["rejected"], "empty_tree"]}
    tracker.attach("integrity", report)
    if not report["intact"]:
        bad = len(report["mismatched"]) + len(report["missing"]) + len(report["rejected"])
        tracker.step("integrity", "failed", files=bad, algorithm=report["algorithm"])
        return False
    tracker.step("integrity", "done", files=report["matched"], algorithm=report["algorithm"],
                 fingerprint=report["fingerprint"][:16])
    return True
