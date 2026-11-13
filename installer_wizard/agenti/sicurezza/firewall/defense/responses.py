import re
import time
from dataclasses import asdict, dataclass

from agenti.firewall import model

KINDS = ("tarpit", "rate_limit", "honeypot", "quarantine", "sinkhole", "country_block")
IP_ONLY = frozenset({"tarpit", "rate_limit", "honeypot", "sinkhole", "country_block"})
COUNTRY = re.compile(r"^[A-Z]{2}$")
MAX_ACTIVE = 512


@dataclass(frozen=True)
class Response:
    kind: str
    target: str
    family: str
    expires: float
    reason: str = ""
    auto: bool = False
    at: float = 0.0

    @property
    def key(self) -> str:
        return key(self.kind, self.target)

    def export(self) -> dict:
        return asdict(self)

    def live(self, now: float | None = None) -> bool:
        return not self.expires or self.expires > (now or time.time())


def key(kind: str, target: str) -> str:
    return f"{kind}:{target}"


def build(kind: str, target: str, minutes: float, reason: str = "", auto: bool = False, at: float | None = None,
          expires: float | None = None) -> Response:
    if kind not in KINDS:
        raise ValueError(f"risposta sconosciuta: {kind}")
    now = at or time.time()
    if kind == "country_block":
        code = str(target or "").removeprefix("country:").strip().upper()
        if not COUNTRY.match(code) or code == "ZZ":
            raise ValueError(f"codice paese non valido: {target}")
        value, family = code, "country"
    else:
        address = model.address(str(target or ""))
        if address.family == "set" or (kind in IP_ONLY and address.family == "mac"):
            raise ValueError(f"indirizzo non valido per {kind}: {target}")
        value, family = address.value, address.family
    if expires is None or expires <= 0:
        span = max(1.0, min(float(minutes), 525_600.0))
        expires = now + span * 60
    return Response(kind, value, family, float(expires), model.comment(reason)[:80], bool(auto), float(now))


def restore(item: dict) -> Response:
    if not isinstance(item, dict):
        raise ValueError("risposta non valida")
    return build(str(item.get("kind")), str(item.get("target")), 1, str(item.get("reason", "")), bool(item.get("auto")),
                 float(item.get("at") or time.time()), float(item.get("expires") or 0.0) or None)
