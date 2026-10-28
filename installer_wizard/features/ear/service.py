import asyncio
import json
import logging
import os
import re
import secrets
import time

import numpy as np
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [nuxiva.ear] %(levelname)s: %(message)s")
for noisy in ("websockets", "faster_whisper"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

import earconf
import enhance
import capture
import feedback
import stt
from broadcast import SESSIONS, broadcast_event, park_hidden, register, unregister
from learner import current_name, learner, name_variant
from music import MusicTap
from livecap import LiveCaptions
from livegov import LiveGovernor
from recorder import Recorder, write_chunk
from reviewer import Reviewer, activity
from voiceprint import ENROLLED_AT, Voiceprints
from wakeword import WakeWord
from autolevel import AutoLevel
from host_mic import HostMicCapture

log = logging.getLogger("nuxiva.ear")

RATE = 16000
PORT = int(os.environ.get("NUXIVA_EAR_PORT", "8093"))
FRAME = 480
PRE_ROLL = int(0.4 * RATE)
END_SILENCE = earconf.number("NUXIVA_EAR_END_SILENCE", 0.65, 0.3, 1.5)
CONVERSATION_S = earconf.number("NUXIVA_EAR_CONVERSATION_S", 30.0, 5.0, 120.0)
MAX_UTTERANCE = 14.0
MIN_UTTERANCE = 0.35
WAIT_FOR_SPEECH = 8.0
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
BARGE_IN = float(os.environ.get("NUXIVA_BARGE_IN", "0.7"))

voiceprints = Voiceprints()
governor = LiveGovernor()
LINK_FILE = os.environ.get("NUXIVA_EAR_LINK", "/var/lib/nuxiva/ear_link.json")
HOST_MIC: HostMicCapture | None = None
LINK = {"clients": 0, "last_audio": 0.0, "level": 0.0, "since": time.time(), "pages": []}


def save_link() -> None:
    try:
        tmp = LINK_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({**LINK, "at": time.time()}, f)
        os.replace(tmp, LINK_FILE)
    except OSError as exc:
        log.debug("Stato del collegamento non salvato: %s", exc)


async def link_writer() -> None:
    while True:
        LINK["live"] = governor.status()
        LINK["host_mic"] = bool(HOST_MIC and HOST_MIC.is_capturing())
        save_link()
        await asyncio.sleep(5)


class Session:

    def __init__(self, ws) -> None:
        self.ws = ws
        self.buffer = np.zeros(0, dtype=np.float32)
        self.ring = np.zeros(0, dtype=np.float32)
        self.noise = 0.004
        self.in_speech = False
        self.speech: list = []
        self.speech_start = 0.0
        self.last_voice = 0.0
        self.mode = "idle"
        self.listen_until = 0.0
        self.conversation = False
        self.awaiting_command = False
        self.instant = False
        self.nuxiva_speaking = False
        self.last_level = 0.0
        self.waiting = 0
        self.raw: list | None = None
        self.alone: str | None = None
        self.enroll: dict | None = None
        self.music = MusicTap()
        self.profile = enhance.NoiseProfile()
        self.wake = WakeWord()
        self.autolevel = AutoLevel()
        self.recorder = Recorder(secrets.token_hex(3))
        self.page: dict = {}
        self.opened = time.time()
        self.last_pcm_time = 0.0
        self.lang = stt.HOME_LANG
        self.live = LiveCaptions(self.broadcast, governor, stt.live_transcribe, self._identify_live, stt.lock)

    async def send(self, **event) -> None:
        try:
            await self.ws.send(json.dumps(event))
        except websockets.ConnectionClosed:
            pass

    async def broadcast(self, **event) -> None:
        await broadcast_event(self, **event)

    async def set_mode(self, mode: str, seconds: float = WAIT_FOR_SPEECH, conversation: bool = False) -> None:
        self.mode = mode
        self.conversation = conversation and mode == "listening"
        self.listen_until = time.time() + seconds if mode == "listening" else 0.0
        await self.broadcast(type="state", state=mode, conversation=self.conversation)

    async def feed(self, pcm: bytes) -> None:
        if not self.page and time.time() - self.opened > 5 and any(s.page.get("visible") == "visible" for s in SESSIONS):
            log.info("Connessione senza identità chiusa: c'è una pagina visibile del display")
            await self.ws.close(4001, "pagina non identificata")
            return
        if self.raw is not None:
            self.raw.append(pcm)
            return
        self.last_pcm_time = time.time()
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        LINK["last_audio"] = time.time()
        if len(samples):
            LINK["level"] = round(float(np.sqrt(np.mean(samples * samples))), 4)
        self.buffer = np.concatenate([self.buffer, samples])
        while len(self.buffer) >= FRAME:
            frame, self.buffer = self.buffer[:FRAME], self.buffer[FRAME:]
            await self._frame(frame)

    async def _frame(self, frame: np.ndarray) -> None:
        now = time.time()
        rms = float(np.sqrt(np.mean(frame * frame)) + 1e-9)
        leveled = self.autolevel.apply(frame, rms, self.noise)
        advice = self.autolevel.take_advice()
        if advice:
            LINK["mic_level"] = advice
            await self.send(type="mic_level", advice=advice)
        self.music.feed(frame, rms, self.noise, self.mode == "idle" and not self.nuxiva_speaking, now)
        threshold = max(self.noise * 3.2, 0.010)
        voiced = rms > threshold
        if voiced:
            activity.voice()
        chunk = self.recorder.feed(frame, rms, voiced or self.in_speech, self.noise, now,
                                   self.nuxiva_speaking or self.enroll is not None or self.music.playing,
                                   self.profile.magnitude)
        if chunk is not None:
            asyncio.create_task(self._save(chunk))
        if now - self.last_level > 0.1:
            self.last_level = now
            await self.broadcast(type="level", rms=round(min(1.0, rms * 12), 3), speech=self.in_speech,
                                 wake=round(self.wake.score, 2))

        if self.nuxiva_speaking:
            self.in_speech, self.speech = False, []
            await self._drop_caption()
            if self.enroll is None and self.wake.feed(frame) and self.wake.score >= BARGE_IN:
                self.nuxiva_speaking = False
                await self.broadcast(type="barge")
                await self._instant_wake()
            return
        if self.mode == "idle" and self.enroll is None and self.wake.feed(leveled):
            await self._instant_wake()
        if self.mode == "listening" and now > self.listen_until and (not self.in_speech or now > self.listen_until + 6):
            await self._listen_timeout()

        if not self.in_speech:
            if not voiced:
                self.noise = self.noise * 0.97 + rms * 0.03
                self.profile.learn(frame)
            self.ring = np.concatenate([self.ring, frame])[-PRE_ROLL:]
            if voiced:
                self.in_speech, self.speech_start, self.last_voice = True, now, now
                self.speech = [self.ring.copy()]
                self.live.begin(self._addressed())
            return

        self.speech.append(frame)
        self.live.tick(self.speech, self.lang, self._addressed())
        if voiced:
            self.last_voice = now
        duration = now - self.speech_start
        if now - self.last_voice > END_SILENCE or duration > MAX_UTTERANCE:
            audio = np.concatenate(self.speech)
            self.in_speech, self.speech, self.ring = False, [], np.zeros(0, dtype=np.float32)
            instant, self.instant = self.instant, False
            caption = self.live.end()
            if duration >= MIN_UTTERANCE:
                asyncio.create_task(self._utterance(audio, self.mode == "listening" or instant,
                                                    self.conversation, instant, caption))
            elif caption["utt"]:
                await self.broadcast(type="caption_drop", utt=caption["utt"])

    async def _save(self, chunk) -> None:
        try:
            await asyncio.to_thread(write_chunk, chunk)
        except OSError as exc:
            note_error("salvataggio della registrazione", exc)

    def _addressed(self) -> bool:
        return self.mode == "listening" or self.instant

    async def _drop_caption(self) -> None:
        caption = self.live.end()
        if caption["utt"]:
            await self.broadcast(type="caption_drop", utt=caption["utt"])

    def _identify_live(self, audio: np.ndarray) -> tuple:
        slug, score = voiceprints.identify(voiceprints.embed(audio))
        return slug, score, self._known(slug)

    async def _listen_timeout(self) -> None:
        if self.in_speech:
            self.in_speech, self.speech, self.ring = False, [], np.zeros(0, dtype=np.float32)
            await self._drop_caption()
        if self.awaiting_command:
            self.awaiting_command = False
            learner.on_false_wake()
            self.recorder.note("false_wake")
        if self.conversation:
            await self.broadcast(type="conversation_end")
        await self.set_mode("idle")

    async def _instant_wake(self) -> None:
        self.instant = True
        self.awaiting_command = True
        learner.on_wake(None, 0)
        self.recorder.note("wake", source="instant", score=round(self.wake.score, 2))
        await self.broadcast(type="wake", source="instant")
        await self.set_mode("listening")

    async def _utterance(self, audio: np.ndarray, attentive: bool, followup: bool, instant: bool, caption: dict) -> None:
        self.recorder.hold(20)
        if not await asyncio.to_thread(stt.has_speech, audio):
            await self.broadcast(type="caption_drop", utt=caption["utt"])
            if instant:
                await self._wake_only()
            elif attentive and self.mode == "listening" and time.time() > self.listen_until:
                await self.set_mode("idle")
            return
        clean = await asyncio.to_thread(enhance.clean, audio, self.profile)
        if self.enroll is not None:
            await self.broadcast(type="caption_drop", utt=caption["utt"])
            await self._enroll_sample(clean, audio)
            return
        if not attentive and self.waiting >= 2:
            await self.broadcast(type="caption_drop", utt=caption["utt"])
            return
        self.waiting += 0 if attentive else 1
        woke = instant
        overheard = None
        try:
            async with stt.lock:
                t = time.time()
                if not attentive:
                    stt.refresh_hotwords()
                    probe, _ = await asyncio.to_thread(stt.transcribe, stt.head(clean), True, False)
                    if not learner.find_wake(probe):
                        learner.on_miss(probe)
                        self.recorder.note("heard", text=probe)
                        overheard = await self._overheard(clean, probe, caption)
                    else:
                        woke = True
                        self.recorder.note("wake", source="speech")
                        await self.broadcast(type="wake", source="speech")
                if overheard is None:
                    await self.broadcast(type="state", state="transcribing", conversation=followup)
                    text, lang = await asyncio.to_thread(stt.transcribe, clean, False, True)
                    ms = int((time.time() - t) * 1000)
        finally:
            self.waiting -= 0 if attentive else 1
        if overheard is not None:
            await self._heard(overheard, clean, caption)
            return
        await self._deliver(text, lang, ms, clean, woke, followup, caption)

    async def _overheard(self, clean: np.ndarray, probe: str, caption: dict) -> str:
        if capture.journal_on() and capture.full_text_on() and len(clean) > len(stt.head(clean)) and governor.background_ok():
            full, _ = await asyncio.to_thread(stt.transcribe, clean, True, False)
            if full and not stt.hallucination(full):
                return full
        return caption["text"] or probe

    async def _heard(self, text: str, clean: np.ndarray, caption: dict) -> None:
        if not text.strip():
            await self.broadcast(type="caption_drop", utt=caption["utt"])
            return
        slug, score = await asyncio.to_thread(lambda: voiceprints.identify(voiceprints.embed(clean)))
        await self.broadcast(type="heard", text=text, utt=caption["utt"], speaker=slug, speaker_score=round(score, 3),
                             voice_known=self._known(slug))
        asyncio.create_task(capture.store(note_error, "heard", text, self.lang, slug, score, False, 0, caption, clean))

    async def _deliver(self, text: str, lang: str, ms: int, clean: np.ndarray, woke: bool, followup: bool,
                       caption: dict) -> None:
        self.lang = lang
        found = learner.find_wake(text)
        command = text[found[1]:].strip(" ,.!?") if found and found[0] < 3 else text.strip()
        log.info("Sentito (%d ms, attivazione=%s, conversazione=%s): %s", ms, woke, followup, text)
        if woke and found:
            learner.on_wake(found[2], ms)
        if stt.hallucination(command) or len(command) <= 2:
            await self.broadcast(type="caption_drop", utt=caption["utt"])
            if woke or self.awaiting_command:
                await self._wake_only()
            else:
                await self.set_mode("idle")
            return
        self.awaiting_command = False
        learner.on_command()
        self.recorder.note("transcript", text=command, dur=round(len(clean) / RATE, 2), woke=woke, ms=ms)
        speaker, score = await asyncio.to_thread(self._speaker, clean)
        asyncio.create_task(capture.store(note_error, "command", command, lang, speaker, score, woke, ms, caption, clean))
        enforce_speaker = earconf.flag("NUXIVA_VOICEPRINT_ENFORCE", False)
        if enforce_speaker and voiceprints.ready and len(voiceprints.samples) > 0:
            if not speaker:
                log.info("Voce non riconosciuta tra i profili registrati (score=%.2f): comando ignorato per sicurezza", score)
                await self.broadcast(type="caption_drop", utt=caption["utt"])
                await self.set_mode("idle")
                return

        await self.broadcast(type="transcript", text=command, ms=ms, lang=lang, followup=followup and not woke,
                             speaker=speaker, speaker_score=round(score, 3), voice_known=self._known(self.alone),
                             utt=caption["utt"])
        auto_followup = earconf.number("NUXIVA_EAR_AUTO_FOLLOWUP", 8.0, 0.0, 30.0)
        if auto_followup > 0.0:
            await self.set_mode("listening", seconds=auto_followup, conversation=True)
        else:
            await self.set_mode("idle")

    def _speaker(self, clean: np.ndarray) -> tuple[str | None, float]:
        emb = voiceprints.embed(clean)
        slug, score = voiceprints.identify(emb)
        if emb is not None and self.alone and slug in (None, self.alone):
            voiceprints.add(self.alone, emb, "ascolto")
        return slug, score

    @staticmethod
    def _known(slug: str | None) -> bool | None:
        if not slug or not voiceprints.ready:
            return None
        return voiceprints.count(slug) >= ENROLLED_AT

    async def _wake_only(self) -> None:
        self.awaiting_command = True
        await self.broadcast(type="wake_only")
        await self.set_mode("listening")

    async def _enroll_sample(self, clean: np.ndarray, raw: np.ndarray) -> None:
        emb = await asyncio.to_thread(voiceprints.embed, clean) if voiceprints.ready else None
        if emb is not None:
            self.enroll["count"] = await asyncio.to_thread(voiceprints.add, self.enroll["slug"], emb, "lettura")
        if not self.enroll.get("train"):
            await self.send(type="enroll_progress", count=self.enroll["count"], ok=emb is not None)
            return
        expect = self.enroll.get("expect")
        stt.refresh_hotwords()
        async with stt.lock:
            heard, _ = await asyncio.to_thread(stt.transcribe, clean, False, True)
        variant = name_variant(heard) if expect in ("wake", "command") else None
        taught = bool(variant) and learner.teach(variant)
        matched = variant is not None if expect in ("wake", "command") else bool(heard.strip())
        peak = float(np.abs(raw).max()) if len(raw) else 0.0
        level = {"rms": round(float(np.sqrt(np.mean(raw * raw))) if len(raw) else 0.0, 4), "peak": round(peak, 4),
                 "clipping": round(float(np.mean(np.abs(raw) >= 0.985)) if len(raw) else 0.0, 4),
                 "advice": self.autolevel.status()["advice"]}
        await self.send(type="enroll_progress", count=self.enroll["count"], ok=matched, heard=heard, variant=variant,
                        taught=taught, level=level, expect=expect, name=current_name())

    async def _transcribe_raw(self) -> None:
        pcm, self.raw = b"".join(self.raw or []), None
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        async with stt.lock:
            text, lang = (await asyncio.to_thread(stt.transcribe, enhance.clean(audio, self.profile), False, True)
                          if len(audio) > RATE * 0.3 else ("", stt.HOME_LANG))
        await self.send(type="transcription", text=text, lang=lang)

    async def control(self, msg: dict) -> None:
        kind = msg.get("type")
        if kind == "listen":
            learner.on_manual_listen()
            await self.set_mode("listening")
        elif kind == "followup":
            seconds = max(3.0, min(120.0, float(msg.get("seconds", 8))))
            if msg.get("conversation"):
                seconds = max(seconds, CONVERSATION_S)
            await self.set_mode("listening", seconds, conversation=bool(msg.get("conversation")))
        elif kind == "speaking":
            self.nuxiva_speaking = bool(msg.get("on"))
            if self.nuxiva_speaking:
                self.wake.reset()
        elif kind == "presence":
            alone = str(msg.get("alone") or "")
            self.alone = alone if SLUG_RE.match(alone) else None
        elif kind == "enroll_start":
            slug = str(msg.get("slug") or "")
            if SLUG_RE.match(slug) and (voiceprints.ready or msg.get("train")):
                count = voiceprints.count(slug) if voiceprints.ready else 0
                self.enroll = {"slug": slug, "count": count, "train": bool(msg.get("train")), "expect": ""}
                stt.HOTWORDS["at"] = 0.0
                await self.send(type="enroll_progress", count=self.enroll["count"], ok=True)
            else:
                await self.send(type="enroll_unavailable")
        elif kind == "enroll_expect" and self.enroll is not None:
            expect = str(msg.get("kind") or "")
            self.enroll["expect"] = expect if expect in ("wake", "command", "reading") else ""
        elif kind == "enroll_stop":
            done, self.enroll = self.enroll, None
            await self.send(type="enroll_done", count=(done or {}).get("count", 0))
        elif kind == "transcribe_start":
            self.raw = []
        elif kind == "transcribe_end":
            await self._transcribe_raw()
        elif kind == "stats":
            await self.send(type="stats", **learner.summary(), instant=self.wake.ready, voiceprint=voiceprints.ready)
        elif kind == "client":
            self.page = {"page": str(msg.get("page") or "")[:12], "visible": str(msg.get("visible") or "")[:10],
                         "href": str(msg.get("href") or self.page.get("href", ""))[:60], "since": self.page.get("since", time.time())}
            LINK["pages"] = [s.page for s in SESSIONS if s.page]
            await park_hidden()
        elif kind == "cancel":
            self.in_speech, self.speech = False, []
            await self._drop_caption()
            await self.set_mode("idle")


def note_error(where: str, exc: Exception) -> None:
    text = f"{where}: {type(exc).__name__}: {exc}"[:240]
    if LINK.get("error") != text:
        log.exception("Errore nell'ascolto (%s)", where)
    LINK["error"], LINK["error_at"] = text, time.time()


async def handler(ws) -> None:
    try:
        session = Session(ws)
    except Exception as exc:
        note_error("avvio della sessione", exc)
        save_link()
        raise
    await session.send(type="ready", model=stt.MODEL_SIZE, instant=session.wake.ready, voiceprint=voiceprints.ready, host_mic=bool(HOST_MIC and HOST_MIC.is_capturing()))
    log.info("Display collegato")
    register(session)
    LINK["clients"] += 1
    save_link()
    try:
        async for message in ws:
            try:
                if isinstance(message, bytes):
                    await session.feed(message)
                else:
                    await session.control(json.loads(message))
            except (ValueError, TypeError) as exc:
                if isinstance(message, bytes):
                    note_error("elaborazione dell'audio", exc)
                else:
                    log.debug("Messaggio di controllo non valido")
            except websockets.ConnectionClosed:
                raise
            except Exception as exc:
                note_error("elaborazione dell'audio" if isinstance(message, bytes) else "comando", exc)
                session.in_speech, session.speech = False, []
                session.live.end()
    except websockets.ConnectionClosed:
        log.debug("Connessione chiusa dal display")
    finally:
        unregister(session)
        LINK["pages"] = [s.page for s in SESSIONS if s.page]
        LINK["clients"] = max(0, LINK["clients"] - 1)
        save_link()
        log.info("Display scollegato")


async def main() -> None:
    global HOST_MIC
    reviewer = Reviewer(lambda: any(s.mode != "idle" or s.in_speech or s.nuxiva_speaking for s in SESSIONS))
    HOST_MIC = host_mic = HostMicCapture(Session)
    async with websockets.serve(handler, "127.0.0.1", PORT, max_size=2 ** 20, ping_interval=20, ping_timeout=90):
        await asyncio.gather(link_writer(), reviewer.run(), capture.maintenance(), feedback.run(voiceprints), host_mic.run())


if __name__ == "__main__":
    asyncio.run(main())
