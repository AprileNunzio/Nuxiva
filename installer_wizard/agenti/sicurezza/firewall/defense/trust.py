import hmac
import ipaddress
import json
import logging
import secrets
import threading
import time

from config import STATE_DIR
from state import store as system_store

from agenti.firewall import model
from agenti.firewall.defense.journal import journal
from agenti.firewall.store import store

META_FILE = STATE_DIR / "firewall" / "trust.json"
PENDING_SECONDS = 300
MAX_PENDING = 16
MAX_ATTEMPTS = 5
log = logging.getLogger("nuxiva.firewall")


class TrustError(ValueError):
    pass


def risks_of(address: model.Address) -> list[str]:
    if address.family == "mac":
        return []
    network = ipaddress.ip_network(address.value, strict=False)
    found = []
    if not (network.is_private or network.is_link_local):
        found.append("internet")
    if (network.version == 4 and network.prefixlen < 24) or (network.version == 6 and network.prefixlen < 64):
        found.append("wide_network")
    return found


class Trust:

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.pending: dict[str, dict] = {}
        self.meta: dict[str, dict] = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(META_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}

    def _save(self) -> None:
        META_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = META_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.meta, ensure_ascii=False), encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(META_FILE)

    def request(self, raw: str, label: str, by: str) -> dict:
        from agenti.network.whois import device, label as name_of
        address = model.address(str(raw or ""))
        if address.family == "set":
            raise TrustError("un gruppo non può essere affidabile")
        found = device(address.value) or {}
        addresses = [model.text_of(address)]
        mac = str(found.get("mac") or "")
        if address.family != "mac" and model.MAC.match(mac):
            addresses.append(mac)
        now = time.time()
        with self.lock:
            for key in [k for k, p in self.pending.items() if p["expires"] < now]:
                del self.pending[key]
            if len(self.pending) >= MAX_PENDING:
                raise TrustError("troppe richieste in sospeso: riprova tra qualche minuto")
            entry = {"id": secrets.token_hex(8), "code": f"{secrets.randbelow(1_000_000):06d}", "addresses": addresses,
                     "label": model.comment(label or (name_of(address.value) if found else ""))[:60], "risks": risks_of(address),
                     "expires": now + PENDING_SECONDS, "by": by, "attempts": 0}
            self.pending[entry["id"]] = entry
        return {k: v for k, v in entry.items() if k not in ("by", "attempts")}

    def confirm(self, rid: str, code: str, accept_risks: bool) -> dict:
        with self.lock:
            entry = self.pending.get(str(rid))
            if entry is None or entry["expires"] < time.time():
                self.pending.pop(str(rid), None)
                raise TrustError("richiesta scaduta o sconosciuta: ricomincia")
            if not hmac.compare_digest(str(code or ""), entry["code"]):
                entry["attempts"] += 1
                if entry["attempts"] >= MAX_ATTEMPTS:
                    del self.pending[entry["id"]]
                raise TrustError("codice di conferma errato")
            if entry["risks"] and not accept_risks:
                raise TrustError("conferma anche i rischi indicati prima di procedere")
            return self.pending.pop(entry["id"])

    def remember(self, addresses: list[str], label: str, by: str) -> None:
        with self.lock:
            for key in addresses:
                self.meta[key] = {"label": model.comment(label)[:60], "at": time.time(), "by": model.comment(by)[:40]}
            self._save()

    def forget(self, addresses: list[str]) -> None:
        with self.lock:
            for key in addresses:
                self.meta.pop(key, None)
            self._save()

    def listing(self) -> list[dict]:
        from agenti.network.whois import who
        with store.lock:
            trusted = [model.text_of(a) for a in store.policy.trusted]
        out = []
        for key in trusted:
            info = who(key) or {}
            meta = self.meta.get(key, {})
            out.append({"address": key, "label": meta.get("label") or info.get("label", ""), "since": meta.get("at", 0),
                        "by": meta.get("by", ""), "online": bool(info.get("online")), "known": bool(info.get("known"))})
        return out


async def apply(addresses: list[str], trusted: bool, user: str, label: str = "") -> dict:
    from agenti.firewall.applier import FirewallError, applier
    with store.lock:
        store.checkpoint(f"{', '.join(addresses)} {'affidabile' if trusted else 'non più affidabile'}")
        current = {model.text_of(a): a for a in store.policy.trusted}
        for raw in addresses:
            target = model.address(raw)
            key = model.text_of(target)
            if trusted:
                current[key] = target
                store.blocks.pop(target.value, None)
                for rkey in [k for k, r in store.responses.items() if r.target == target.value]:
                    del store.responses[rkey]
            else:
                current.pop(key, None)
        store.policy = model.policy({"trusted": list(current)}, store.policy)
        store.save()
    try:
        outcome = await applier.apply(f"dispositivi affidabili aggiornati da {user}")
    except FirewallError:
        store.rollback()
        raise
    (trust.remember(addresses, label, user) if trusted else trust.forget(addresses))
    journal.record(action="trust" if trusted else "untrust", kind="trust", target=", ".join(addresses)[:80], by=user, ok=True,
                   detail=label)
    system_store.event("INFO", f"Firewall · {', '.join(addresses)} {'ora affidabile' if trusted else 'non più affidabile'} (da {user})",
                       "firewall")
    return outcome


trust = Trust()
