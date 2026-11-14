import logging
import threading
import time

from autonomy import profile, stt
from autonomy.local_ear import LocalEar
from autonomy.tts import LocalSpeechError, SapiSpeech
from connection.client import Client, ServerError
from connection.ear import EarStream
from permissions.catalog import Level
from permissions.policy import Policy
from i18n.strings import t
from settings import agent_name, paths
from voice.microphone import Microphone
from voice.speaker import Speaker
from voice.stream import speak_stream, split_reply

log = logging.getLogger("nuxiva.voice")


def i18n_language() -> str:
    return t.language
FOLLOWUP_SECONDS = 8


class Voice:
    def __init__(self, client: Client, cfg: dict, policy: Policy, ui, on_security) -> None:
        self.client, self.cfg, self.policy, self.ui = client, cfg, policy, ui
        self.speaker = Speaker()
        self.mode = profile.parse_mode(cfg.get("mode"))
        self.has_server = bool(cfg.get("server") and cfg.get("token"))
        self.ear = EarStream(client, self.on_event, self.on_link, on_security)
        tier = profile.recommend(profile.detect())
        engine = stt.pick_engine(cfg.get("stt_model") or tier.stt_model, str(paths.DATA_DIR / "models"), tier.gpu,
                                 i18n_language())
        self.local_ear = LocalEar(engine, lambda: [agent_name.clean(cfg.get("agent_name")), "nuxiva"], self.on_event)
        self.local_tts = SapiSpeech()
        self.server_down_until = 0.0
        self.mic = Microphone(self._audio, cfg.get("mic_device"))
        self.speaking = False
        self.busy = lambda: False
        self.on_transcript = None
        self._reply_lock = threading.Lock()
        self._reply_cancel: threading.Event | None = None

    def continuous(self) -> bool:
        return self.policy.level("senses.microphone") is not Level.DENY

    def _server_ear(self) -> bool:
        return self.has_server and self.mode is not profile.Mode.LOCAL and self.ear.connected

    def _active_ear(self):
        if self._server_ear():
            return self.ear
        if self.mode is not profile.Mode.SERVER and self.local_ear.enabled:
            return self.local_ear
        return None

    def _audio(self, pcm: bytes) -> None:
        ear = self._active_ear()
        if ear is not None:
            ear.send_audio(pcm)

    def _send(self, **message) -> None:
        if self.has_server:
            self._send(**message)
        self.local_ear.send(**message)

    def start(self) -> None:
        if self.has_server and self.mode is not profile.Mode.LOCAL:
            self.ear.start()
        if self.mode is not profile.Mode.SERVER:
            self.local_ear.start()
        self.mic.start()
        self.mic.muted = not self.continuous()
        if self.mic.error:
            self.ui.dispatch.post(self.ui.note, "⚠ " + self.mic.error)
        threading.Thread(target=self._levels, daemon=True, name="levels").start()

    def stop(self) -> None:
        self.ear.stop()
        self.local_ear.stop()
        self.mic.stop()
        self.stop_reply()

    def stop_reply(self) -> None:
        with self._reply_lock:
            if self._reply_cancel is not None:
                self._reply_cancel.set()
            self.speaker.stop()

    def _levels(self) -> None:
        while True:
            self.ui.set_level(self.speaker.level if self.speaking else self.mic.level)
            time.sleep(0.033)

    def on_link(self, ok: bool, error: str) -> None:
        self.ui.dispatch.post(self.ui.set_state, "idle" if ok or self.local_ear.enabled else "offline")

    def on_event(self, event: dict) -> None:
        kind, post = event.get("type"), self.ui.dispatch.post
        if event.get("origin") is False and kind in ("wake", "wake_only", "transcript", "barge", "state"):
            return
        if kind == "wake":
            self.speaker.chime(True)
            post(self.ui.set_state, "listening")
            post(self.ui.show_panel)
        elif kind == "state":
            state = event.get("state")
            if state == "listening" and not self.busy():
                post(self.ui.set_state, "listening")
            elif state == "transcribing":
                post(self.ui.set_state, "thinking")
            elif state == "idle" and not self.busy() and not self.speaking:
                self.mic.muted = not self.continuous()
                post(self.ui.set_state, "idle")
        elif kind == "transcript" and (event.get("text") or "").strip():
            self.on_transcript(event["text"].strip(), event.get("lang"))
        elif kind == "barge":
            self.stop_reply()
        elif kind == "wake_only":
            post(self.ui.set_state, "listening")
        elif kind == "mic_level" and event.get("advice") == "lower":
            post(self.ui.note, "🎙 Il microfono è un po' troppo alto: abbassalo nelle impostazioni audio di Windows.")

    def listen(self) -> None:
        self.stop_reply()
        if self._active_ear() is None:
            self.ui.show_panel(focus=True)
            self.ui.note("🎙 Ascolto vocale non disponibile ora: scrivimi pure qui.")
            return
        self.mic.muted = False
        self._send(type="listen")
        self.speaker.chime(True)
        self.ui.set_state("listening")
        self.ui.show_panel()

    def set_muted(self, muted: bool) -> None:
        self.mic.muted = muted
        self.ui.note("🔇 Microfono in pausa" if muted else "🎙 Microfono attivo")

    def answer(self, reply: str, lang: str | None, spoken: bool) -> None:
        if reply and self.cfg.get("voice"):
            self._speak(reply, lang)
        elif spoken:
            self._send(type="followup", seconds=FOLLOWUP_SECONDS, conversation=True)

    def _speak(self, text: str, lang: str | None) -> None:
        cancelled = threading.Event()
        with self._reply_lock:
            self._reply_cancel = cancelled
        try:
            self._play_reply(text, lang, cancelled)
        finally:
            with self._reply_lock:
                if self._reply_cancel is cancelled:
                    self._reply_cancel = None

    def _synthesize(self, chunk: str, lang: str | None) -> bytes:
        if self.has_server and self.mode is not profile.Mode.LOCAL and time.monotonic() >= self.server_down_until:
            try:
                return self.client.tts(chunk, lang)
            except ServerError as exc:
                if self.mode is profile.Mode.SERVER:
                    raise
                self.server_down_until = time.monotonic() + 30
                log.info("Voce del server non disponibile, uso quella locale: %s", exc)
        if self.mode is profile.Mode.SERVER:
            raise ServerError("voce del server non disponibile")
        return self.local_tts.synthesize(chunk, lang)

    def _play_reply(self, text: str, lang: str | None, cancelled: threading.Event) -> None:
        chunks = split_reply(text)
        if not chunks:
            return
        was_muted = self.mic.muted
        started = False

        def begin() -> None:
            nonlocal started
            started = True
            self.speaking = True
            self.ui.dispatch.post(self.ui.set_state, "speaking")
            self._send(type="speaking", on=True)
            if not self.cfg.get("headset"):
                self.mic.muted = True

        def failed(exc: Exception) -> None:
            log.info("Voce non disponibile: %s", exc)

        try:
            speak_stream(chunks, lambda chunk: self._synthesize(chunk, lang),
                         lambda wav: self.speaker.play_wav(wav, cancelled), cancelled, begin, failed,
                         (ServerError, LocalSpeechError))
        finally:
            if started:
                self.mic.muted = was_muted
                self.speaking = False
                self._send(type="speaking", on=False)
                if not cancelled.is_set():
                    self._send(type="followup", seconds=FOLLOWUP_SECONDS, conversation=True)
                self.ui.dispatch.post(self.ui.set_state, "idle")
