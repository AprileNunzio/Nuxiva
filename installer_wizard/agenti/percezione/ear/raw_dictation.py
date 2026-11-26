import asyncio

import numpy as np

import enhance
import stt

RATE = 16000
MIN_SECONDS = 0.3


async def transcribe_raw(session) -> None:
    pcm, session.raw = b"".join(session.raw or []), None
    audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    async with stt.lock:
        text, lang = (await asyncio.to_thread(stt.transcribe, enhance.clean(audio, session.profile), False, True)
                      if len(audio) > RATE * MIN_SECONDS else ("", stt.HOME_LANG))
    await session.send(type="transcription", text=text, lang=lang)
