import base64
import getpass
import logging
import socket
import threading
import time
import uuid

from actions.executor import Executor
from app import report
from connection import tls
from connection.client import Client, ServerError, Unauthorized
from i18n.strings import t
from intents import screenshot as shot
from intents import senses, site
from permissions.gate import Denied, Gate, Request
from permissions.policy import Policy
from senses import capture, reading
from senses.windows import Focus

log = logging.getLogger("nuxiva.conversation")
MAX_ROUNDS = 4
HIDE_DELAY = 0.35
TEXT_MIN = 120


class Conversation:
    def __init__(self, client: Client, executor: Executor, gate: Gate, policy: Policy, focus: Focus, ui, voice,
                 environment, backend=None, screenshots=None) -> None:
        self.backend = backend or client
        self.screenshots = screenshots
        self.client, self.executor, self.gate, self.policy = client, executor, gate, policy
        self.focus, self.ui, self.voice, self.environment = focus, ui, voice, environment
        self.busy = threading.Lock()
        self._turn_lock = threading.Lock()
        self._request_id = None
        self._cancelled = False
        self.on_unauthorized = None
        self.on_security = None

    def ask(self, text: str, lang: str | None = None, spoken: bool = False) -> None:
        threading.Thread(target=self._ask, args=(text, lang, spoken), daemon=True, name="ask").start()

    def stop(self) -> None:
        with self._turn_lock:
            self._cancelled = True
            request_id = self._request_id
        self.voice.stop_reply()
        if request_id:
            threading.Thread(target=self._stop_request, args=(request_id,), daemon=True, name="stop-assist").start()

    def _stop_request(self, request_id: str) -> None:
        try:
            self.client.stop_assist(request_id)
        except (ServerError, Unauthorized, tls.PinMismatch) as exc:
            log.warning("Arresto remoto non confermato: %s", exc)

    def _request(self, body: dict) -> dict:
        with self._turn_lock:
            if self._cancelled:
                return {"cancelled": True}
            request_id = uuid.uuid4().hex
            self._request_id = request_id
        try:
            return self.backend.assist({**body, "turn_id": request_id})
        finally:
            with self._turn_lock:
                self._request_id = None

    def _post(self, fn, *args) -> None:
        self.ui.dispatch.post(fn, *args)

    def _body(self, text: str, lang: str | None) -> dict:
        window = self.focus.current()
        return {"text": text, "lang": lang or "",
                "env": {**self.environment(), "user": getpass.getuser(), "host": socket.gethostname(),
                        "permissions": self.policy.summary()},
                "context": {"window": window.title if window else "", "app": window.app if window else ""}}

    def _capture(self, need: str, body: dict, explicit: bool = True) -> None:
        window = self.focus.current()
        if need == "webcam":
            self.gate.check(Request("senses.webcam", t("senses.webcam.confirm"), body["text"]), always_ask=not explicit)
            self._post(self.ui.note, t("senses.webcam.note"))
            body["image"], body["image_source"] = base64.b64encode(capture.webcam_image()).decode(), "webcam"
            return
        where = f"«{window.title[:60]}»" if window else t("senses.screen.whole")
        self.gate.check(Request("senses.screen", t("senses.screen.confirm", where=where), body["text"]),
                        always_ask=not explicit)
        content = reading.window_text(window) if window else ""
        if len(content) >= TEXT_MIN:
            body["context"]["content"] = content
            self._post(self.ui.note, t("senses.screen.reading", where=where))
        else:
            body["image"], body["image_source"] = base64.b64encode(capture.window_image(window)).decode(), "screen"
            self._post(self.ui.note, t("senses.screen.looking", where=where))

    def _execute(self, actions: list, executed: list) -> list:
        lines, results = self.executor.run(actions or [])
        for line in lines:
            self._post(self.ui.note, line)
        executed.extend(results)
        return results

    def _rounds(self, body: dict, executed: list) -> dict:
        result: dict = {}
        research_requested = False
        for _ in range(MAX_ROUNDS):
            result = self._request(body)
            body.pop("research_approved", None)
            if self._cancelled or result.get("cancelled"):
                return {"cancelled": True}
            if result.get("ignored") or result.get("error"):
                return result
            if result.get("need") == "research":
                if research_requested:
                    return result
                self.gate.check(Request("research.web", t("research.confirm"), body["text"]), always_ask=True)
                body["research_approved"] = True
                research_requested = True
                continue
            need = result.get("need")
            if need and not body.get("image") and not body["context"].get("content"):
                if need == "webcam" and not senses.asks_webcam(body["text"]):
                    log.info("Webcam richiesta dal modello senza domanda esplicita: rifiutata")
                    return {"reply": t("senses.webcam.not_requested"), "lang": result.get("lang")}
                self._capture(need, body, explicit=senses.asks_screen(body["text"]))
                continue
            results = self._execute(result.get("actions") or [], executed)
            if result.get("followup") and results:
                body.pop("image", None)
                body["results"] = results
                continue
            return result
        return result

    def _direct(self, text: str, body: dict, executed: list) -> dict | None:
        intent = site.parse(text)
        if intent is None:
            return None
        action = {"type": "open_url", "url": intent.url}
        if intent.browser:
            action["browser"] = intent.browser
        log.info("Intento diretto: apertura sito %s (browser: %s)", intent.host, intent.browser or "predefinito")
        self._execute([action], executed)
        return {"reply": "", "lang": body.get("lang") or None}

    def _screenshot(self, text: str, lang: str | None) -> dict:
        self.ui.dispatch.call(self.ui.hide_panel)
        time.sleep(HIDE_DELAY)
        outcome = self.screenshots.shoot()
        message = self.screenshots.message(outcome)
        self._post(self.ui.show_panel)
        self._post(self.ui.say, "user", text)
        log.info("Intento diretto: screenshot (%s)", outcome.status)
        if outcome.status == "delivered":
            return {"reply": t("screenshot.voice_saved"), "show": message, "lang": lang or None}
        return {"reply": message, "lang": lang or None}

    def _ask(self, text: str, lang: str | None, spoken: bool) -> None:
        with self.busy:
            with self._turn_lock:
                self._cancelled = False
            wants_shot = self.screenshots is not None and shot.asks(text)
            if not wants_shot:
                self._post(self.ui.show_panel)
                self._post(self.ui.say, "user", text)
                self._post(self.ui.set_state, "thinking")
            body = self._body(text, lang)
            if spoken and hasattr(self.voice, "recent_audio_pcm16_b64"):
                audio_b64 = self.voice.recent_audio_pcm16_b64()
                if audio_b64:
                    body["audio_pcm16_b64"] = audio_b64
                    body["audio_sample_rate"] = 16000
            executed: list[dict] = []
            try:
                result = self._screenshot(text, lang) if wants_shot else self._direct(text, body, executed)
                if result is None:
                    if senses.asks_webcam(text):
                        self._capture("webcam", body)
                    elif senses.asks_screen(text):
                        self._capture("screen", body)
                    result = self._rounds(body, executed)
            except Denied as exc:
                self._post(self.ui.say, "nuxiva", t("assist.denied", reason=str(exc)))
                self._post(self.ui.set_state, "idle")
                return
            except Unauthorized:
                self.on_unauthorized()
                return
            except tls.PinMismatch as exc:
                self.on_security(str(exc))
                return
            except (ServerError, capture.CaptureError) as exc:
                log.warning("Richiesta non riuscita: %s", exc)
                self._post(self.ui.say, "nuxiva", t("assist.failed", reason=str(exc)))
                self._post(self.ui.set_state, "error")
                return
            except Exception as exc:
                log.exception("Errore imprevisto durante l'assistenza: %s", exc)
                self._post(self.ui.say, "nuxiva", t("assist.unexpected", reason=str(exc)))
                self._post(self.ui.set_state, "error")
                return
            self._finish(result, executed, lang, spoken)

    def _finish(self, result, executed: list, lang: str | None, spoken: bool) -> None:
        if not isinstance(result, dict) or self._cancelled or result.get("cancelled") or result.get("ignored"):
            self._post(self.ui.set_state, "idle")
            return
        if result.get("error"):
            log.warning("Il server non ha trovato un cervello: %s", result.get("error"))
            self._post(self.ui.say, "nuxiva", report.error_message(result["error"]))
            self._post(self.ui.set_state, "error")
            return
        reply = report.compose(str(result.get("reply") or ""), executed)
        show = str(result.get("show") or "").strip()
        if not reply and not show:
            reply = t("assist.nothing_to_add")
        self._post(self.ui.say, "nuxiva", reply, show if show else None)
        try:
            self.voice.answer(reply, result.get("lang") or lang, spoken, result.get("voice_modulation"))
        except Exception as exc:
            log.warning("Riproduzione vocale non riuscita: %s", exc)
        self._post(self.ui.set_state, "idle")
