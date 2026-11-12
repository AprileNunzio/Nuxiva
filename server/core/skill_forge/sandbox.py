import json
import logging
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Mapping

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.skill_forge.contracts import MAX_SPEECH_CHARS

logger = logging.getLogger("nuxiva.skill_forge.sandbox")

RUNNER = Path(__file__).with_name("runner.py")
WALL_SECONDS = 4.0
MAX_OUTPUT_BYTES = 65_536
KILLED_BY_LIMIT = frozenset({-9, -24, -getattr(signal, "SIGXCPU", 24)})
KILLED_BY_FILTER = -getattr(signal, "SIGSYS", 31)
LAYERS = ("namespaces", "no_new_privs", "seccomp")

_observed: dict[str, bool] = {}
_observed_lock = threading.Lock()


def isolation_report() -> dict[str, Any]:
    with _observed_lock:
        seen = dict(_observed)
    if not seen:
        return {"observed": False, "layers": {}, "complete": False, "degraded": []}
    degraded = [layer for layer in LAYERS if not seen.get(layer)]
    return {"observed": True, "layers": {layer: bool(seen.get(layer)) for layer in LAYERS}, "complete": not degraded,
            "degraded": degraded}


def _remember(isolation: Any) -> None:
    if not isinstance(isolation, dict):
        return
    with _observed_lock:
        _observed.clear()
        _observed.update({layer: bool(isolation.get(layer)) for layer in LAYERS})
    missing = [layer for layer in LAYERS if not isolation.get(layer)]
    if missing:
        logger.warning("Skill sandbox running with reduced isolation (missing: %s)", ", ".join(missing))


def _validated(output: Any) -> Result[dict[str, Any], CortexFailure]:
    if not isinstance(output, dict) or not isinstance(output.get("speech"), str):
        return fail("cortex.forge.output_invalid")
    if not output["speech"].strip() or len(output["speech"]) > MAX_SPEECH_CHARS:
        return fail("cortex.forge.output_invalid")
    return Ok(output)


def run_isolated(source: str, slots: Mapping[str, Any]) -> Result[dict[str, Any], CortexFailure]:
    try:
        payload = json.dumps({"source": source, "slots": dict(slots)}, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        return fail("cortex.forge.output_invalid")
    with tempfile.TemporaryDirectory(prefix="skill-") as workdir:
        try:
            done = subprocess.run(
                [sys.executable, "-I", "-S", str(RUNNER)],
                input=payload, capture_output=True, timeout=WALL_SECONDS, cwd=workdir, env={}, check=False,
            )
        except subprocess.TimeoutExpired:
            return fail("cortex.forge.timeout")
        except OSError as exc:
            logger.error("Cannot start the skill sandbox (%s)", type(exc).__name__)
            return fail("platform.sandbox.unavailable")
    if done.returncode == KILLED_BY_FILTER:
        logger.error("Skill attempted a forbidden system call and was terminated")
        return fail("cortex.forge.violation")
    if done.returncode in KILLED_BY_LIMIT:
        return fail("cortex.forge.timeout")
    if len(done.stdout) > MAX_OUTPUT_BYTES:
        return fail("cortex.forge.output_invalid")
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        logger.warning("Skill sandbox produced no result (exit %s)", done.returncode)
        return fail("cortex.forge.runtime_failed")
    _remember(reply.get("isolation"))
    if not reply.get("ok"):
        logger.warning("Skill failed with %s", reply.get("error"))
        return fail("cortex.forge.runtime_failed", reason=str(reply.get("error")))
    return _validated(reply.get("result"))
