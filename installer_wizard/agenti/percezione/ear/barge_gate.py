import asyncio
import logging
import time

import numpy as np

import barge
import window_gate
from collaudo_tap import probe
from duplex_link import link

log = logging.getLogger("nuxiva.ear.barge_gate")


def _runner_up(scores: dict, slug) -> float:
    others = [float(v) for k, v in scores.items() if k != slug]
    return max(others) if others else 0.0


def evaluate(voiceprints, window: np.ndarray, voiced: bool, music: bool, programme: bool, echo_cancelled: bool, gate=None) -> tuple:
    judge = gate.judge if gate is not None else barge.PyBarge.judge_window
    probe = voiceprints.embed(window) if voiced else None
    if probe is None:
        return judge(False, False, 0.0, 0.0, 0.0, music, programme, echo_cancelled)
    result = voiceprints.verdict(probe)
    slug = result.get("slug")
    scores = voiceprints.scores(probe)
    score = float(scores.get(slug, result.get("score") or 0.0)) if slug else float(result.get("score") or 0.0)
    limit = voiceprints.limit(slug) if slug else 1.0
    args = (True, slug is not None, score, _runner_up(scores, slug), limit, music, programme, echo_cancelled)
    return judge(*args, slug) if gate is not None else judge(*args)


async def observe(service, frame: np.ndarray, voiced: bool, music: bool) -> None:
    state = service.__dict__.get("_gate_buf")
    if not (link.active() and service.nuxiva_speaking and service.echo_cancelled_input and service.voiceprints.ready):
        if state is not None:
            state["gate"].reset()
            state["t0"] = 0.0
        if not service.nuxiva_speaking:
            service.__dict__.pop("_aec_noted", None)
        return
    if not service.__dict__.get("_aec_noted"):
        service.__dict__["_aec_noted"] = True
        probe("aec_active", active=1)
    if state is None:
        state = service.__dict__.setdefault("_gate_buf", {"gate": window_gate.build(), "t0": 0.0})
    if voiced and not state["t0"]:
        state["t0"] = time.monotonic()
    window = state["gate"].push(np.ascontiguousarray(frame, dtype="<f4").tobytes(), voiced)
    if window is None:
        return
    raw, was_voiced = window
    started = state["t0"] or time.monotonic()
    state["t0"] = 0.0
    try:
        verdict, margin = await asyncio.to_thread(evaluate, service.voiceprints, np.frombuffer(raw, dtype="<f4"), was_voiced, music, service._programme(), True, state["gate"])
    except (ValueError, RuntimeError, TypeError, OSError) as exc:
        log.warning("verdetto per finestra non disponibile: %s", type(exc).__name__)
        verdict, margin = state["gate"].judge(False, False, 0.0, 0.0, 0.0, music, False, True)
    finally:
        state["gate"].release()
    if link.barge_step(verdict, margin, was_voiced) == "cut":
        probe("barge_in", stop_ms=round((time.monotonic() - started) * 1000))
        service.nuxiva_speaking = False
        state["gate"].reset()
        await service.broadcast(type="barge", reason="voice")
        await service.broadcast(type="duplex", **link.snapshot())
