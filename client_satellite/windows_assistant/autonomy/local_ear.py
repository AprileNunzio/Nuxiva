import logging
import queue
import threading

from autonomy.segmenter import Segmenter
from autonomy.wake import WakeGate

log = logging.getLogger("nuxiva.localear")
BACKLOG = 4


class LocalEar:
    def __init__(self, engine, names, on_event, on_status=None) -> None:
        self.engine, self.on_event, self.on_status = engine, on_event, on_status
        self.gate = WakeGate(names)
        self.segmenter = Segmenter()
        self.jobs: queue.Queue = queue.Queue(maxsize=BACKLOG)
        self.stop_flag = threading.Event()
        self.connected = True
        self.enabled = False
        self.thread = threading.Thread(target=self._run, daemon=True, name="local-ear")
        self.listening = False

    def start(self) -> None:
        self.enabled = bool(self.engine.ready())
        if self.enabled:
            self.thread.start()
            if self.on_status:
                self.on_status(True, "")

    def stop(self) -> None:
        self.stop_flag.set()
        self.jobs.put(None)

    def send_audio(self, pcm: bytes) -> None:
        if not self.enabled:
            return
        for utterance in self.segmenter.feed(pcm):
            try:
                self.jobs.put_nowait(utterance)
            except queue.Full:
                log.info("Riconoscimento locale in ritardo: frase scartata")

    def send(self, **message) -> None:
        kind = message.get("type")
        if kind == "listen":
            self.listening = True
        elif kind == "followup":
            self.gate.open_followup(float(message.get("seconds") or 8))

    def _run(self) -> None:
        while not self.stop_flag.is_set():
            audio = self.jobs.get()
            if audio is None:
                return
            self.on_event({"type": "state", "state": "transcribing", "origin": True})
            try:
                text, lang = self.engine.transcribe(audio)
            except (RuntimeError, ValueError, OSError) as exc:
                log.warning("Riconoscimento locale non riuscito: %s", exc)
                self.on_event({"type": "state", "state": "idle", "origin": True})
                continue
            self._route(text, lang)

    def _route(self, text: str, lang: str) -> None:
        directed = self.gate.process(text)
        forced, self.listening = self.listening, False
        if directed is None and not forced:
            self.on_event({"type": "state", "state": "idle", "origin": True})
            return
        remainder, kind = directed if directed is not None else (" ".join(text.split()), "forced")
        if kind == "wake":
            self.on_event({"type": "wake", "origin": True})
        command = self.gate.command_text(text, remainder) if kind == "wake" else text.strip()
        if command:
            self.on_event({"type": "transcript", "text": command, "lang": lang or None, "origin": True})
        else:
            self.on_event({"type": "wake_only", "origin": True})
