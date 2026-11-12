import asyncio
import logging
import os

import numpy as np

import earconf
import stt
from vote import vote

log = logging.getLogger("nuxiva.ear")
RATE = 16000
MARGIN_S = 0.4
FUSED_WEIGHT = 1.5
MIN_SCORE_DB = 6.0
MAX_MICS = 4


def enabled() -> bool:
    mode = os.environ.get("NUXIVA_EAR_MODE", "offline").strip().lower()
    return earconf.flag("NUXIVA_EAR_VOTE", True) and mode not in ("online", "hybrid")


def pick(channels: list, count: int) -> list:
    usable = [c for c in channels if len(c) == 3 and c[2] and float(c[1]) >= MIN_SCORE_DB]
    return sorted(usable, key=lambda c: -float(c[1]))[:count]


async def agree(provider, clean: np.ndarray, text: str, lang: str) -> str:
    if provider is None or not text.strip() or lang != stt.HOME_LANG or not enabled():
        return text
    count = int(earconf.number("NUXIVA_EAR_VOTE_MICS", 2, 0, MAX_MICS))
    channels = provider.recent(len(clean) + int(MARGIN_S * RATE)) if count else []
    if len(channels) < 2:
        return text
    hypotheses = [(text, FUSED_WEIGHT)]
    for name, score, pcm in pick(channels, count):
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        heard, _ = await asyncio.to_thread(stt.transcribe, audio, False, False)
        if heard.strip() and not stt.hallucination(heard):
            hypotheses.append((heard, min(1.2, max(0.5, float(score) / 20.0))))
            log.info("Microfono %s ha capito: %s", name, heard)
    if len(hypotheses) < 2:
        return text
    voted, agreement, changed = vote(hypotheses)
    log.info("Voto tra %d ascolti (accordo %.0f%%, parole cambiate %d): %s", len(hypotheses), agreement * 100, changed, voted)
    return voted or text
