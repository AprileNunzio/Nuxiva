import asyncio
import logging

import numpy as np

import barge
from duplex_link import link

log = logging.getLogger("nuxiva.ear.barge_gate")
WINDOW = 4000
MAX_PENDING = 8000


def _runner_up(scores: dict, slug) -> float:
    others = [float(v) for k, v in scores.items() if k != slug]
    return max(others) if others else 0.0


def evaluate(voiceprints, window: np.ndarray, voiced: bool, music: bool, programme: bool, echo_cancelled: bool) -> tuple:
    probe = voiceprints.embed(window) if voiced else None
    if probe is None:
        return barge.PyBarge.judge_window(False, False, 0.0, 0.0, 0.0, music, programme, echo_cancelled)
    result = voiceprints.verdict(probe)
    slug = result.get("slug")
    scores = voiceprints.scores(probe)
    score = float(scores.get(slug, result.get("score") or 0.0)) if slug else float(result.get("score") or 0.0)
    limit = voiceprints.limit(slug) if slug else 1.0
    judge = barge.native().judge_window if barge.native() is not None else barge.PyBarge.judge_window
    return judge(True, slug is not None, score, _runner_up(scores, slug), limit, music, programme, echo_cancelled)


async def observe(service, frame: np.ndarray, voiced: bool, music: bool) -> None:
    if not (link.active() and service.nuxiva_speaking and service.echo_cancelled_input and service.voiceprints.ready):
        service.__dict__.pop("_gate_buf", None)
        return
    buf = service.__dict__.setdefault("_gate_buf", {"audio": np.zeros(0, dtype=np.float32), "voiced": 0, "busy": False})
    buf["audio"] = np.concatenate([buf["audio"], frame])[-MAX_PENDING:]
    buf["voiced"] += int(voiced)
    if len(buf["audio"]) < WINDOW or buf["busy"]:
        return
    window, was_voiced = buf["audio"][-WINDOW:], buf["voiced"] * 2 >= len(buf["audio"]) // len(frame)
    buf["audio"], buf["voiced"], buf["busy"] = np.zeros(0, dtype=np.float32), 0, True
    try:
        verdict, margin = await asyncio.to_thread(evaluate, service.voiceprints, window, was_voiced, music, service._programme(), True)
    except (ValueError, RuntimeError, TypeError, OSError) as exc:
        log.warning("verdetto per finestra non disponibile: %s", type(exc).__name__)
        verdict, margin = "uncertain", 0
    finally:
        buf["busy"] = False
    if link.barge_step(verdict, margin, was_voiced) == "cut":
        service.nuxiva_speaking = False
        await service.broadcast(type="barge", reason="voice")
        await service.broadcast(type="duplex", **link.snapshot())
