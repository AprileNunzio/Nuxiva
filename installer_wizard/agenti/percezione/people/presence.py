import asyncio
import logging
import time

import httpx

from agenti.people import people
from config import env_get
from state import store

log = logging.getLogger("nuxiva.people.presence")
VISION_URL = "http://127.0.0.1:8091"
GREET_AGAIN_AFTER = 20 * 60
UNKNOWN_GREET_AFTER = 5 * 60
STABLE_SECONDS = 1.2
HOLD_SECONDS = 15.0
LANGUAGE_TTL = 30.0


def _join(names: list) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]


def _salutation() -> str:
    h = time.localtime().tm_hour
    if 5 <= h < 13:
        return "Buongiorno"
    if 13 <= h < 18:
        return "Buon pomeriggio"
    return "Buonasera" if 18 <= h < 23 else "Buonanotte"


def describe(people: list) -> str:
    known = sorted({p["name"] for p in people if p["known"]})
    unknown = sum(1 for p in people if not p["known"])
    if not people:
        return "Al momento non vedo nessuno davanti alla webcam."
    parts = []
    if known:
        parts.append(f"Vedo {_join(known)}")
    if unknown:
        who = "una persona che non conosco" if unknown == 1 else f"{unknown} persone che non conosco"
        parts.append(("e " if known else "Vedo ") + who)
    return " ".join(parts) + "."


def merge(visible: list) -> list:
    known: dict = {}
    unknown = []
    for p in visible:
        if not p.get("known"):
            unknown.append(p)
            continue
        seen = known.get(p["slug"])
        if not seen:
            known[p["slug"]] = dict(p)
            continue
        seen["near"] = seen.get("near") or p.get("near")
        seen["since"] = min(seen.get("since", p["since"]), p["since"])
        seen["confidence"] = max(seen.get("confidence", 0), p.get("confidence", 0))
    return [*known.values(), *unknown]


class PresenceMonitor:
    def __init__(self) -> None:
        self.held: dict = {}
        self.unknown_held: tuple = ([], 0.0)
        self.last_seen: dict = {}
        self.greeted: dict = {}
        self.last_unknown_greet = 0.0
        self.greeting_id = 0
        self.observed: dict = {}
        self.languages: dict = {}
        self.affect_at: dict = {}
        self.updated_at = 0.0

    def smooth(self, visible: list) -> list:
        now = time.time()
        people_now = merge(visible)
        for p in people_now:
            if p.get("known"):
                previous = self.held.get(p["slug"])
                since = min(p["since"], previous[0]["since"]) if previous else p["since"]
                self.held[p["slug"]] = ({**p, "since": since}, now)
        self.held = {k: v for k, v in self.held.items() if now - v[1] < HOLD_SECONDS}
        unknown = [p for p in people_now if not p.get("known")]
        if unknown:
            self.unknown_held = (unknown, now)
        elif now - self.unknown_held[1] >= HOLD_SECONDS:
            self.unknown_held = ([], 0.0)
        return [p for p, _ in self.held.values()] + self.unknown_held[0]

    def _affect(self, visible: list) -> None:
        from agenti.medico.wellbeing import service as wellbeing
        for p in visible:
            if p.get("known") and p.get("slug") and isinstance(p.get("affect"), dict) and p["affect"].get("at") != self.affect_at.get(p["slug"]):
                self.affect_at[p["slug"]] = p["affect"].get("at")
                reading = wellbeing.ingest(p["slug"], p["affect"])
                if reading and not reading.get("calibrating"):
                    self._journal(p["slug"], wellbeing.live(p["slug"]))

    @staticmethod
    def _details(looks: list) -> None:
        if not looks:
            return
        from agenti.people.details import learner
        try:
            learner.ingest(looks)
        except (OSError, ValueError, KeyError) as exc:
            log.warning("Dettagli dell'aspetto non salvati: %s", exc)

    @staticmethod
    def _vitals_targets() -> list[str]:
        from agenti.medico.vitals.camera import camera
        return camera.targets(store.presence.get("people") or [])

    @staticmethod
    def _vitals(data: dict, visible: list, wanted: list[str]) -> None:
        from agenti.medico.vitals.camera import camera
        if wanted:
            camera.ingest(visible, data.get("vitals_cost"), wanted)

    @staticmethod
    def _journal(slug: str, live: dict | None) -> None:
        from agenti.people import learning
        try:
            learning.learn_face(slug, live)
        except (KeyError, ValueError, OSError) as exc:
            log.warning("Stato d'animo dal volto di %s non salvato: %s", slug, exc)

    def _greet(self, text: str, names: list, slug: str = "", timing: tuple[float, float] | None = None) -> None:
        from agenti.locale import service
        lang = service.preferred(slug)
        if lang == "it":
            self._announce(text, names, timing, slug)
            return
        from tasks import background
        background(self._translated(text, names, lang, timing, slug))

    async def _translated(self, text: str, names: list, lang: str, timing: tuple[float, float] | None, slug: str = "") -> None:
        from agenti.locale.pivot import pivot
        self._announce(await pivot.from_pivot(text, lang, force=True), names, timing, slug)

    def _announce(self, text: str, names: list, timing: tuple[float, float] | None = None, slug: str = "") -> None:
        self.greeting_id += 1
        now = time.time()
        greeting = {"id": self.greeting_id, "text": text, "names": names, "slug": slug, "at": now}
        if timing and timing[0] <= timing[1] <= now:
            detected_at, identity_at = timing
            durations = {
                "face_to_identity_ms": round((identity_at - detected_at) * 1000),
                "identity_to_greeting_ms": round((now - identity_at) * 1000),
            }
            greeting["timing"] = durations
            log.info(
                "greeting_timing face_to_identity_ms=%d identity_to_greeting_ms=%d",
                durations["face_to_identity_ms"],
                durations["identity_to_greeting_ms"],
            )
        store.greeting = greeting
        self._audience()
        store.event("INFO", f"Saluto: {text}", "vision")

    def _evaluate(self, people_list: list) -> None:
        now = time.time()
        stable = [p for p in people_list if now - p["since"] >= STABLE_SECONDS
                  and (p.get("liveness") or {}).get("state") != "spoof"]
        arrivals = []
        for p in stable:
            if not p["known"]:
                continue
            away = now - self.last_seen.get(p["slug"], 0)
            if away > GREET_AGAIN_AFTER and now - self.greeted.get(p["slug"], 0) > GREET_AGAIN_AFTER:
                arrivals.append(p)
        for p in people_list:
            if p["known"]:
                self.last_seen[p["slug"]] = now
                if now - self.observed.get(p["slug"], 0) > 5:
                    self.observed[p["slug"]] = now
                    people.observe(p["slug"], p["name"], now)

        unknown_near = [p for p in stable if not p["known"] and p["near"]]
        newcomers = [p for p in arrivals if p.get("auto")]
        arrivals = [p for p in arrivals if not p.get("auto")]
        for p in newcomers:
            self.greeted[p["slug"]] = now
            self._greet(f"{_salutation()}! Non ci conoscevamo: l'ho aggiunta alla mia memoria come {p['name']}. "
                        "Mi dica pure come si chiama, per esempio: mi chiamo e il suo nome.", [])
        if arrivals:
            names = sorted({p["name"] for p in arrivals})
            for p in arrivals:
                self.greeted[p["slug"]] = now
            text = f"{_salutation()}, {_join(names)}."
            today = {r["slug"]: r for r in people.reminders(days=0)}
            for p in arrivals:
                r = today.get(p["slug"])
                if r and r["type"] == "compleanno":
                    text += f" Tanti auguri di buon compleanno, {p['name'].split()[0]}!"
                elif r and r["type"] == "onomastico":
                    text += " Oggi è il suo onomastico: auguri!"
                elif r:
                    text += f" Le ricordo: {r['title']}."
            if len(stable) > len(arrivals):
                text += " " + describe(stable)
            arrival = arrivals[0]
            identity_at = arrival.get("identity_at")
            timing = (arrival["since"], identity_at) if len(arrivals) == 1 and isinstance(identity_at, (int, float)) else None
            self._greet(text, names, arrival["slug"], timing)
            from agenti.people.welcome import welcome
            from tasks import background
            background(welcome([p["slug"] for p in arrivals]))
            from agenti.autonomy.engine import autonomy
            autonomy.on_event("arrival")
        elif unknown_near and now - self.last_unknown_greet > UNKNOWN_GREET_AFTER:
            self.last_unknown_greet = now
            if len(stable) > 1:
                text = f"{_salutation()}. {describe(stable)}"
            else:
                text = f"{_salutation()}. Non credo di conoscerti: posso esserti utile?"
            self._greet(text, [])

    def _publish(self, data: dict, visible: list) -> None:
        people = [{k: p.get(k) for k in ("slug", "name", "known", "confidence", "liveness", "near")} for p in visible]
        objects = data.get("objects", [])[:20]
        signature = (tuple((p["slug"], p["near"]) for p in people), tuple((o.get("label"), o.get("held")) for o in objects))
        now = time.time()
        if signature == getattr(self, "_bus_sig", None) and now - getattr(self, "_bus_at", 0.0) < 10:
            return
        self._bus_sig, self._bus_at = signature, now
        from agenti.people import percept
        percept.note_people([p["slug"] for p in people if p.get("known")])
        capture = data.get("capture")
        if isinstance(capture, dict) and capture.get("active"):
            percept.note_scene(capture.get("scene"))
        try:
            from nuxiva_bus import BusError, nuxiva_bus
            nuxiva_bus.publish("vision.presence", {"people": people}, origin="vision", retain=True)
            if objects:
                nuxiva_bus.publish("vision.objects", {"source": "main", "objects": objects, "frame": data.get("frame") or [0, 0],
                                                      "people": people}, origin="vision")
        except (ImportError, BusError):
            pass

    def with_languages(self, visible: list) -> list:
        now = time.time()
        for p in visible:
            if not p.get("known"):
                continue
            cached = self.languages.get(p["slug"])
            if not cached or now - cached[1] > LANGUAGE_TTL:
                prof = people.load(p["slug"]) or {}
                cached = (people.preferred_languages(p["slug"])[0], now, prof.get("role", "guest"))
                self.languages[p["slug"]] = cached
            p["ui_lang"] = cached[0]
            p["role"] = cached[2] if len(cached) > 2 else "guest"
        return visible

    @staticmethod
    def _audience() -> None:
        from agenti.desktop.presence_bridge import bridge
        try:
            bridge.update()
        except (OSError, ValueError) as exc:
            log.error("Pubblico del display non aggiornato: %s", exc, exc_info=exc)

    @staticmethod
    def _particles() -> None:
        try:
            from agenti.particles import show
            show.tick()
        except (ImportError, ValueError, KeyError, TypeError) as exc:
            log.warning("Figura a particelle non aggiornata: %s", type(exc).__name__)

    async def run(self) -> None:
        async with httpx.AsyncClient(timeout=3) as client:
            while True:
                if env_get("NUXIVA_VISION", "1") == "0":
                    store.presence = {"status": "disabled", "people": [], "summary": ""}
                    await asyncio.sleep(10)
                    continue
                try:
                    wanted = self._vitals_targets()
                    data = (await client.get(f"{VISION_URL}/presence", params={"vitals": ",".join(wanted)} if wanted else None)).json()
                    visible = self.with_languages(self.smooth(data.get("people", [])))
                    looks = [dict(p) for p in visible if p.get("details")]
                    for p in visible:
                        p.pop("details", None)
                    previous = store.presence.get("people", [])
                    store.presence = {"status": data.get("status"), "error": data.get("error", ""),
                                      "people": visible, "summary": describe(visible),
                                      "objects": data.get("objects", [])[:20]}
                    self.updated_at = time.time()
                    self._audience()
                    self._particles()
                    if [(p["name"], p["near"]) for p in visible] != [(p["name"], p["near"]) for p in previous]:
                        store.touch()
                    self._publish(data, visible)
                    self._affect(visible)
                    self._details(looks)
                    self._vitals(data, visible, wanted)
                    if store.phase in ("READY", "DEGRADED"):
                        self._evaluate(visible)
                        from agenti.automations.bus import bus as automation_bus
                        automation_bus.presence(visible)
                except (httpx.HTTPError, ValueError, KeyError):
                    if store.presence.get("status") != "offline":
                        store.presence = {"status": "offline", "people": [], "summary": ""}
                        store.touch()
                    self._audience()
                await asyncio.sleep(0.7)


monitor = PresenceMonitor()
