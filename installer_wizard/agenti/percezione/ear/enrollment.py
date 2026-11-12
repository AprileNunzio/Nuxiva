import asyncio

import numpy as np

import stt
from learner import current_name, learner, name_variant


async def enroll_sample(session, voiceprints, clean: np.ndarray, raw: np.ndarray) -> None:
    emb = await asyncio.to_thread(voiceprints.embed, clean) if voiceprints.ready else None
    if emb is not None:
        session.enroll["count"] = await asyncio.to_thread(voiceprints.add, session.enroll["slug"], emb, "lettura")
    if not session.enroll.get("train"):
        await session.send(type="enroll_progress", count=session.enroll["count"], ok=emb is not None)
        return
    expect = session.enroll.get("expect")
    stt.refresh_hotwords()
    async with stt.lock:
        heard, _ = await asyncio.to_thread(stt.transcribe, clean, False, True)
    variant = name_variant(heard) if expect in ("wake", "command") else None
    taught = bool(variant) and learner.teach(variant)
    matched = variant is not None if expect in ("wake", "command") else bool(heard.strip())
    peak = float(np.abs(raw).max()) if len(raw) else 0.0
    level = {"rms": round(float(np.sqrt(np.mean(raw * raw))) if len(raw) else 0.0, 4), "peak": round(peak, 4),
             "clipping": round(float(np.mean(np.abs(raw) >= 0.985)) if len(raw) else 0.0, 4),
             "advice": session.autolevel.status()["advice"]}
    await session.send(type="enroll_progress", count=session.enroll["count"], ok=matched, heard=heard, variant=variant,
                       taught=taught, level=level, expect=expect, name=current_name())
