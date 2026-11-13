import logging
import time
from collections import deque

from state import store as system_store

from agenti.firewall import model
from agenti.firewall.defense import netaddr, responses
from agenti.firewall.defense.journal import journal
from agenti.firewall.store import store

ADMIN_MEMORY = 86_400.0
log = logging.getLogger("nuxiva.firewall")


class Refused(ValueError):
    pass


class Responder:

    def __init__(self) -> None:
        self.admins: dict[str, float] = {}
        self.warned: deque[tuple[str, float]] = deque(maxlen=512)

    def seen_admin(self, address: str) -> None:
        key = netaddr.canonical(address or "")
        if netaddr.ip(key) is None:
            return
        now = time.time()
        self.admins[key] = now
        for stale in [k for k, at in self.admins.items() if now - at > ADMIN_MEMORY]:
            del self.admins[stale]

    def admin_addresses(self) -> set[str]:
        now = time.time()
        return {k for k, at in self.admins.items() if now - at <= ADMIN_MEMORY}

    def guarded(self) -> set[str]:
        from agenti.firewall.events import protected
        return set(protected()) | self.admin_addresses()

    def check(self, kind: str, target: str) -> None:
        if kind == "country_block":
            from agenti.firewall.defense.geo import geo
            code = target.removeprefix("country:").upper()
            if code in store.policy.home_countries:
                raise Refused(f"{code} è tra i paesi di casa")
            if not geo.ranges(code):
                raise Refused("database dei paesi non disponibile")
            if any(geo.lookup(a) == code for a in self.admin_addresses()):
                raise Refused(f"ti sei collegato di recente da {code}: bloccarlo ti taglierebbe fuori")
            return
        address = model.address(target)
        if address.value in self.guarded():
            raise Refused(f"{address.value} è il server, il router o il tuo dispositivo: bloccarlo ti taglierebbe fuori")
        if store.trusted(address):
            raise Refused(f"{address.value} è un dispositivo affidabile")
        if kind == "quarantine":
            parsed = netaddr.address(address.value)
            if parsed is None or not netaddr.is_lan(parsed):
                raise Refused("la quarantena vale solo per i dispositivi di casa")

    async def execute(self, action: dict, by: str) -> dict:
        kind, target = str(action.get("kind")), str(action.get("target"))
        minutes = max(1, min(int(action.get("minutes") or 60), 525_600))
        reason = f"{'auto' if by == 'auto' else by}: {action.get('reason', '')}"
        try:
            if kind == "warn":
                return self.warn(action)
            self.check(kind, target)
            if kind == "block":
                from agenti.firewall.events import monitor
                outcome = await monitor.block(model.address(target), minutes, reason)
            else:
                outcome = await self._respond(responses.build(kind, target, minutes, reason, by == "auto"))
        except (Refused, ValueError) as exc:
            journal.record(action="refused", kind=kind, target=target, minutes=minutes, reason=reason, by=by, ok=False,
                           detail=str(exc), incident=str(action.get("incident", "")))
            raise
        journal.record(action="apply", kind=kind, target=target, minutes=minutes, reason=reason, by=by,
                       ok=bool(outcome.get("ok", True)), detail=str(outcome.get("error", "")), incident=str(action.get("incident", "")))
        system_store.event("WARN", f"Difesa: {kind} su {target} per {minutes} min ({reason})", "firewall")
        return outcome

    async def _respond(self, response: responses.Response) -> dict:
        from agenti.firewall.applier import FirewallError, applier
        with store.lock:
            if response.key not in store.responses and len(store.responses) >= responses.MAX_ACTIVE:
                raise Refused("troppe difese attive: rimuovine qualcuna")
            store.checkpoint(f"difesa {response.kind} {response.target}")
            store.responses[response.key] = response
            store.save()
        try:
            return await applier.apply(f"difesa {response.kind} su {response.target}")
        except FirewallError:
            with store.lock:
                store.responses.pop(response.key, None)
                store.save()
            raise

    async def revoke(self, key: str, by: str) -> dict:
        from agenti.firewall.applier import applier
        with store.lock:
            found = store.responses.pop(key, None)
            if found is None:
                raise KeyError(key)
            store.checkpoint(f"revoca {key}")
            store.save()
        journal.record(action="revoke", kind=found.kind, target=found.target, by=by, ok=True)
        return await applier.apply(f"revoca della difesa {key}")

    def warn(self, action: dict) -> dict:
        tag = f"{action.get('incident')}:{action.get('reason')}"
        now = time.time()
        if any(t == tag and now - at < 3600 for t, at in self.warned):
            return {"ok": True, "repeated": True}
        self.warned.append((tag, now))
        reason = {"trusted_anomaly": "un dispositivo affidabile si comporta in modo insolito",
                  "protected_source": "il server o il router genera traffico sospetto",
                  "lan_anomaly": "un dispositivo di casa si comporta in modo insolito"}.get(str(action.get("reason")), "attività sospetta")
        system_store.event("WARN", f"Difesa: {reason} ({action.get('target')}), nessun blocco automatico", "firewall")
        journal.record(action="warn", kind="warn", target=str(action.get("target")), reason=str(action.get("reason")), by="auto", ok=True,
                       incident=str(action.get("incident", "")))
        return {"ok": True}

    def active(self) -> list[dict]:
        with store.lock:
            return [{**r.export(), "key": r.key} for r in sorted(store.responses.values(), key=lambda r: r.at, reverse=True)]


responder = Responder()
