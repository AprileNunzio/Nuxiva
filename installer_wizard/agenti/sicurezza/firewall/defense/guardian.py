import asyncio
import logging
import time
from collections import deque

from state import store as system_store

from agenti.firewall import model
from agenti.firewall.defense import engine, netaddr
from agenti.firewall.defense.geo import GeoError, geo, refresh
from agenti.firewall.store import store

EVERY = 30.0
HOUR = 3600.0
MAX_STRIKES = 4096
EMPTY = {"posture": "calm", "incidents": [], "actions": [], "countries": [], "internet": 0, "lan": 0}
log = logging.getLogger("nuxiva.firewall")


def policy_view(policy: model.Policy) -> dict:
    return {"autonomy": policy.autonomy, "mode": policy.mode, "window_s": 1800.0, "min_level": policy.auto_block_severity,
            "block_minutes": policy.auto_block_minutes, "max_minutes": policy.max_block_minutes, "tarpit": policy.tarpit,
            "honeypot": policy.honeypot, "quarantine": policy.quarantine, "country_block": policy.country_block,
            "country_threshold": policy.country_threshold, "home_countries": list(policy.home_countries),
            "max_actions_per_hour": policy.max_actions_per_hour}


class Guardian:

    def __init__(self) -> None:
        self.assessment: dict = {**EMPTY, "at": 0.0, "engine": engine.engine_name()}
        self.strikes: dict[str, int] = {}
        self.performed: deque[float] = deque(maxlen=1024)
        self.posture = "calm"
        self.task: asyncio.Task | None = None

    def recent_actions(self, now: float) -> int:
        return sum(1 for at in self.performed if now - at <= HOUR)

    def strike(self, target: str) -> None:
        key = netaddr.canonical(target)
        if key not in self.strikes and len(self.strikes) >= MAX_STRIKES:
            self.strikes.pop(next(iter(self.strikes)))
        self.strikes[key] = min(self.strikes.get(key, 0) + 1, 1000)
        self.performed.append(time.time())

    def payload(self, alerts: list[dict], protected: set[str], now: float) -> dict:
        with store.lock:
            policy = store.policy
            trusted = [model.text_of(a) for a in policy.trusted]
            active = list(store.blocks) + [r.target if r.family != "country" else f"country:{r.target}"
                                           for r in store.responses.values()]
            view = policy_view(policy)
        clean = [{k: a[k] for k in ("kind", "severity", "src", "dst", "count", "at")} for a in alerts]
        sources = {netaddr.canonical(a["src"]) for a in clean if a["src"]}
        return {"now": now, "alerts": clean, "policy": view, "trusted": trusted, "protected": sorted(protected),
                "active": active, "strikes": {k: v for k, v in self.strikes.items() if k in sources},
                "countries": geo.countries(sources), "recent_actions": self.recent_actions(now)}

    def evaluate(self, alerts: list[dict], protected: set[str], now: float | None = None) -> dict:
        moment = now or time.time()
        result = engine.assess(self.payload(alerts, protected, moment))
        self.assessment = {**result, "at": moment, "engine": engine.engine_name()}
        if result["posture"] != self.posture:
            previous, self.posture = self.posture, result["posture"]
            level = "ERROR" if self.posture == "attack" else "WARN" if self.posture == "alert" else "INFO"
            system_store.event(level, f"Difesa: stato {previous} → {self.posture}", "firewall")
            self._publish(previous)
        return self.assessment

    def _publish(self, previous: str) -> None:
        try:
            from nuxiva_bus import BusError, nuxiva_bus
        except ImportError:
            return
        try:
            nuxiva_bus.publish("defense.posture", {"posture": self.posture, "previous": previous}, origin="firewall")
        except BusError as exc:
            log.warning("Stato della difesa non pubblicato sul bus: %s", exc)

    def snapshot(self) -> dict:
        from agenti.firewall.defense.honeypot import honeypot
        from agenti.firewall.defense.journal import journal
        from agenti.firewall.defense.responder import responder
        return {**self.assessment, "geo": geo.status(), "responses": responder.active(), "decoy": honeypot.status(),
                "journal": journal.tail(30), "journal_ok": journal.verify()}

    async def on_alert(self, alert: dict) -> None:
        alert["country"] = geo.lookup(alert.get("src", ""))
        self.tick()
        await self.act()

    async def act(self) -> list[dict]:
        from agenti.firewall.applier import FirewallError
        from agenti.firewall.defense.responder import Refused, responder
        done = []
        for action in list(self.assessment.get("actions", [])):
            if not action["auto"] and action["kind"] != "warn":
                continue
            try:
                outcome = await responder.execute(action, "auto")
            except (Refused, ValueError, FirewallError) as exc:
                log.warning("Difesa automatica non applicata su %s: %s", action["target"], exc)
                continue
            if action["kind"] != "warn":
                self.strike(action["target"])
                done.append({**action, "outcome": outcome})
        if done:
            self.tick()
        await self.decoy()
        return done

    async def decoy(self) -> None:
        from agenti.firewall.defense.honeypot import honeypot
        with store.lock:
            wanted = store.policy.honeypot and store.policy.mode in ("protect", "lockdown")
            targets = [r.target for r in store.responses.values() if r.kind == "honeypot"]
        honeypot.allow(targets)
        if wanted and targets:
            await honeypot.start()
        elif honeypot.server is not None and not targets:
            await honeypot.stop()

    def tick(self) -> dict:
        from agenti.firewall.events import monitor, protected
        return self.evaluate(list(monitor.alerts), protected())

    async def _geo(self) -> None:
        try:
            await asyncio.to_thread(geo.load)
        except (GeoError, OSError) as exc:
            log.warning("Database dei paesi non caricato: %s", exc)
        if store.policy.geo_updates and geo.stale():
            try:
                await refresh()
            except (GeoError, OSError) as exc:
                log.warning("Aggiornamento del database dei paesi non riuscito: %s", exc)

    async def run(self) -> None:
        await self._geo()
        last_geo = time.time()
        while True:
            try:
                self.tick()
                await self.act()
            except (ValueError, TypeError, KeyError) as exc:
                log.error("Valutazione della difesa non riuscita: %s", exc)
            if time.time() - last_geo > 86_400:
                last_geo = time.time()
                await self._geo()
            await asyncio.sleep(EVERY)


guardian = Guardian()
