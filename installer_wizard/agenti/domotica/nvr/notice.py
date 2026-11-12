import logging
import threading
import time

log = logging.getLogger("nuxiva.nvr.notice")
TEXTS = {
    "it": ("Avviso di registrazione", "In {rooms} le telecamere registrano anche l'audio. Le registrazioni sono cifrate e puoi chiederne la cancellazione."),
    "en": ("Recording notice", "In {rooms} the cameras also record audio. Recordings are encrypted and you can ask for them to be deleted."),
    "fr": ("Avis d'enregistrement", "Dans {rooms}, les caméras enregistrent aussi le son. Les enregistrements sont chiffrés et vous pouvez demander leur suppression."),
    "es": ("Aviso de grabación", "En {rooms} las cámaras también graban audio. Las grabaciones están cifradas y puedes pedir que se borren."),
}
JOIN = {"it": " e ", "en": " and ", "fr": " et ", "es": " y "}
TTL_S = 120


def language() -> str:
    try:
        from agenti.locale.service import system_reply
        lang = str(system_reply())[:2]
    except ImportError:
        lang = "it"
    return lang if lang in TEXTS else "it"


def places(rows: list[dict]) -> list[str]:
    return sorted({r["room"] or r["name"] for r in rows if r.get("allowed")})


def message(rows: list[dict], lang: str) -> tuple[str, str]:
    names = places(rows)
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + JOIN[lang] + names[-1]
    title, body = TEXTS[lang]
    return title, body.format(rooms=joined)


def _quiet() -> bool:
    try:
        from agenti.automations.bus import bus
        return bool(bus.states.quiet())
    except (ImportError, AttributeError):
        return False


def _show(title: str, text: str, speak: bool) -> None:
    from agenti.desktop.desk import desk
    data = {"icon": "🎙️", "title": title, "text": text[:400], "announce": True}
    if speak:
        data["speak"] = text
    desk.show("notice", data, key="nvr:recording-notice", ttl=TTL_S)


class RecordingNotice:
    def __init__(self, show=_show, quiet=_quiet, clock=time.time) -> None:
        self.show = show
        self.quiet = quiet
        self.clock = clock
        self.lock = threading.Lock()
        self.last_places: tuple = ()
        self.last_spoken = 0.0
        self.pending = False
        self.history: list[dict] = []

    def tick(self, rows: list[dict], settings: dict, force: bool = False) -> dict | None:
        with self.lock:
            current = tuple(places(rows))
            if not settings.get("notice_enabled") or not current:
                self.last_places, self.pending = (), False
                return None
            now = self.clock()
            every = max(1, int(settings.get("notice_repeat_hours", 12))) * 3600
            due = force or self.pending or current != self.last_places or now - self.last_spoken >= every
            if not due:
                return None
            lang = language()
            title, text = message(rows, lang)
            speak = not self.quiet()
            try:
                self.show(title, text, speak)
            except (ImportError, OSError, RuntimeError) as exc:
                log.warning("NVR: avviso di registrazione non mostrato: %s", exc)
                return None
            self.last_places, self.pending = current, not speak
            if speak:
                self.last_spoken = now
            entry = {"at_ms": int(now * 1000), "places": list(current), "spoken": speak, "text": text}
            self.history = [entry, *self.history][:20]
            return entry

    def status(self) -> dict:
        with self.lock:
            return {"places": list(self.last_places), "last_spoken_ms": int(self.last_spoken * 1000), "pending": self.pending,
                    "history": list(self.history)}


notice = RecordingNotice()
