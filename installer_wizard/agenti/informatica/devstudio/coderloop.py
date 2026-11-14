import hashlib
import json
import logging
import re
import threading

log = logging.getLogger("nuxiva.devstudio.loop")

REQUIRED = ("test", "lint", "security")
PROTECTED = ("critic/", "sandbox/", ".github/", ".githooks/")
MAX_ITERATIONS = 5
NAME = re.compile(r"^[a-z0-9._-]{1,64}$")
RUN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustCoderLoop", None)


def draft_from(files: dict) -> str:
    return json.dumps({"schema_version": 1, "files": [
        {"path": path, "bytes": len(data), "digest": hashlib.sha256(data).hexdigest()} for path, data in files.items()]},
        separators=(",", ":"))


def check(name: str, passed: bool, log_text: str = "", severity: str = "") -> dict:
    return {"name": name, "passed": bool(passed), "severity": severity or ("info" if passed else "high"), "log": str(log_text)[:8000]}


def report(artifact: dict, iteration: int, checks: list, run_id: str, verdict: str = "") -> str:
    ok = all(c["passed"] for c in checks)
    return json.dumps({"schema_version": 1, "digest": artifact["digest"], "sandbox_run": run_id, "checks": checks,
                       "verdict": verdict or ("pass" if ok else "fail"), "iteration": iteration}, separators=(",", ":"))


def _normalize(path: str) -> str:
    if not path or len(path) > 240 or path.startswith("/") or "\\" in path or ":" in path or any(ord(c) < 32 for c in path):
        raise PermissionError("loop.path")
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise PermissionError("loop.path")
    return "/".join(parts).lower()


def _redact(text: str, limit: int = 4000) -> str:
    out = []
    for line in text.splitlines():
        low = line.lower()
        if "-----begin" in low:
            line = "[redacted:key]"
        elif any(k in low for k in ("password", "passwd", "secret", "token", "api_key", "apikey", "authorization", "bearer", "credential")) and ("=" in line or ":" in line):
            line = re.split(r"[=:]", line, maxsplit=1)[0] + "= [redacted]"
        else:
            line = re.sub(r"[A-Za-z0-9+/=_.\-]{32,}", "[redacted]", line)
        out.append("| " + "".join(c for c in line if c.isprintable() or c == "\t"))
    return ("\n".join(out) + "\n")[:limit]


class PyLoop:
    def __init__(self, settings_json: str = "") -> None:
        self._issued: set = set()
        self._audit: list = []
        self._lock = threading.Lock()

    def _seal(self, draft: dict) -> dict:
        if draft.get("schema_version") != 1 or not draft.get("files") or len(draft["files"]) > 256:
            raise ValueError("loop.invalid")
        files = []
        for entry in draft["files"]:
            path = _normalize(entry["path"])
            if any((path + "/").startswith(p) for p in PROTECTED):
                raise PermissionError("loop.protected")
            if not re.fullmatch(r"[0-9a-f]{64}", entry["digest"]):
                raise ValueError("loop.digest")
            files.append({"path": path, "bytes": entry["bytes"], "digest": entry["digest"]})
        files.sort(key=lambda f: f["path"])
        if len({f["path"] for f in files}) != len(files):
            raise ValueError("loop.invalid")
        h = hashlib.sha256()
        for f in files:
            h.update(f["path"].encode() + b"\0" + f["digest"].encode() + b"\n")
        return {"schema_version": 1, "files": files, "digest": h.hexdigest()}

    def _judge(self, rep: dict, artifact: dict, iteration: int):
        if rep.get("schema_version") != 1 or rep.get("digest") != artifact["digest"] or rep.get("iteration") != iteration:
            raise ValueError("loop.report")
        if not RUN.fullmatch(str(rep.get("sandbox_run"))) or not rep.get("checks") or len(rep["checks"]) > 64:
            raise ValueError("loop.report")
        names = [c["name"] for c in rep["checks"]]
        if len(set(names)) != len(names) or not all(NAME.fullmatch(n) for n in names):
            raise ValueError("loop.report")
        failed = sorted([c["name"] for c in rep["checks"] if not c["passed"]] + [f"missing.{r}" for r in REQUIRED if r not in names])
        if rep["verdict"] == "inconclusive":
            return "inconclusive", failed, ""
        fp = hashlib.sha256(json.dumps(failed).encode()).hexdigest()
        return ("pass" if not failed else "fail"), failed, fp

    def run(self, coder, critic) -> str:
        feedback, last, repeats, inconclusive = "", None, 0, 0
        for iteration in range(1, MAX_ITERATIONS + 1):
            try:
                artifact = self._seal(json.loads(coder(feedback, iteration)))
            except PermissionError:
                return self._out("escalated", reason="policy_violation", iterations=iteration)
            except (ValueError, KeyError, TypeError, RuntimeError):
                return self._out("escalated", reason="coder_failed", iterations=iteration)
            try:
                rep = json.loads(critic(json.dumps(artifact), iteration))
                verdict, failed, fp = self._judge(rep, artifact, iteration)
            except (ValueError, KeyError, TypeError, RuntimeError):
                return self._out("escalated", reason="critic_failed", iterations=iteration)
            if verdict == "pass":
                with self._lock:
                    self._issued.add(artifact["digest"])
                return self._out("passed", artifact=artifact, report=rep, iterations=iteration)
            if verdict == "inconclusive":
                inconclusive += 1
                if inconclusive >= 2:
                    return self._out("escalated", reason="inconclusive", iterations=iteration)
                continue
            inconclusive = 0
            repeats = repeats + 1 if fp == last else 1
            last = fp
            if repeats >= 2:
                return self._out("escalated", reason="repeated_failure", iterations=iteration)
            text = "".join(f"[{c['name']}]\n{c['log']}\n" for c in rep["checks"] if not c["passed"])
            feedback = json.dumps({"iteration": iteration, "failed": failed, "untrusted_log": _redact(text)})
        return self._out("exhausted", iterations=MAX_ITERATIONS)

    @staticmethod
    def _out(kind: str, **fields) -> str:
        return json.dumps({"outcome": kind, **fields})

    def authorize(self, digest: str, target_json: str, consent: bool) -> str:
        target = json.loads(target_json)
        with self._lock:
            ok = digest in self._issued
            if not ok or target.get("kind") not in ("local", "remote"):
                decision = "denied"
            elif target["kind"] == "local" or consent:
                decision = "allowed"
            else:
                decision = "needs_consent"
            self._audit.append({"digest": digest, "decision": decision})
        return decision

    def revoke(self, digest: str) -> None:
        with self._lock:
            self._issued.discard(digest)

    def audit(self) -> str:
        with self._lock:
            return json.dumps(self._audit[-1024:])


def build(settings_json: str = ""):
    cls = native()
    if cls is not None:
        try:
            return cls(settings_json)
        except ValueError as exc:
            log.error("Ciclo nativo non disponibile: %s", exc)
    return PyLoop(settings_json)


def run_task(files_fn, checks_fn, loop=None) -> dict:
    loop = loop or build()
    current: dict = {"files": {}}

    def coder(feedback_json: str, iteration: int) -> str:
        current["files"] = files_fn(json.loads(feedback_json) if feedback_json else None, iteration)
        return draft_from(current["files"])

    def critic(artifact_json: str, iteration: int) -> str:
        artifact = json.loads(artifact_json)
        checks, run_id = checks_fn({f["path"]: current["files"][_original(current["files"], f["path"])] for f in artifact["files"]}, iteration)
        return report(artifact, iteration, checks, run_id)

    return {"loop": loop, "outcome": json.loads(loop.run(coder, critic))}


def _original(files: dict, lowered: str) -> str:
    return next(name for name in files if name.lower() == lowered)
