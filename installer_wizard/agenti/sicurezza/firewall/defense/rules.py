import math


KINDS = ("port_scan", "host_sweep", "syn_flood", "brute_force", "arp_spoof", "dns_tunnel", "icmp_flood", "exfiltration")
SEVERITIES = ("low", "medium", "high", "critical")
STAGES = ("recon", "disruption", "intrusion", "interception", "exfiltration")
POSTURES = ("calm", "watch", "alert", "attack")
AUTONOMY = ("observe", "assist", "autonomous")
MODES = ("off", "monitor", "protect", "lockdown")
STAGE_OF = {"port_scan": "recon", "host_sweep": "recon", "syn_flood": "disruption", "icmp_flood": "disruption",
            "brute_force": "intrusion", "arp_spoof": "interception", "dns_tunnel": "exfiltration", "exfiltration": "exfiltration"}
SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 55, "critical": 80}
STAGE_POINTS = {"recon": 0, "disruption": 5, "intrusion": 10, "interception": 15, "exfiltration": 15}
MAX_ALERTS = 5000
MAX_LIST = 4096
MAX_INCIDENTS = 200
MAX_TARGETS = 16
MAX_ACTIONS = 200
RECENT = 600.0
ASSIST_MINUTES = 60
U32 = 0xFFFFFFFF
U64 = 0xFFFFFFFFFFFFFFFF
DEFAULT_POLICY = {"autonomy": "assist", "mode": "monitor", "window_s": 1800.0, "min_level": "medium", "block_minutes": 60,
                  "max_minutes": 10_080, "tarpit": True, "honeypot": False, "quarantine": False, "country_block": False,
                  "country_threshold": 5, "home_countries": [], "max_actions_per_hour": 30}


def rank(options: tuple, value: str) -> int:
    return options.index(value)


def fingerprint(text: str) -> str:
    value = 0xCBF29CE484222325
    for byte in text.encode():
        value ^= byte
        value = (value * 0x100000001B3) & U64
    return f"{value:016x}"


def level_of(score: int) -> str:
    return "low" if score < 25 else "medium" if score < 50 else "high" if score < 75 else "critical"


def window(raw) -> float:
    return min(max(raw, 60.0), 86_400.0) if math.isfinite(raw) and raw > 0.0 else 1800.0


def valid_country(raw) -> str | None:
    text = raw if isinstance(raw, str) else ""
    return text if len(text) == 2 and all("A" <= c <= "Z" for c in text) and text != "ZZ" else None


def _u32(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= U32:
        raise ValueError(f"defense.invalid: {name}")
    return value


def _choice(value, options: tuple, name: str) -> str:
    if value not in options:
        raise ValueError(f"defense.invalid: {name}")
    return value


def _flag(value, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"defense.invalid: {name}")
    return value


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"defense.invalid: {name}")
    return float(value)


def _strings(value, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"defense.invalid: {name}")
    return value


def policy_of(raw) -> dict:
    data = {**DEFAULT_POLICY, **(raw or {})}
    return {"autonomy": _choice(data["autonomy"], AUTONOMY, "autonomy"), "mode": _choice(data["mode"], MODES, "mode"),
            "window_s": _number(data["window_s"], "window_s"), "min_level": _choice(data["min_level"], SEVERITIES, "min_level"),
            "block_minutes": _u32(data["block_minutes"], "block_minutes"), "max_minutes": _u32(data["max_minutes"], "max_minutes"),
            "tarpit": _flag(data["tarpit"], "tarpit"), "honeypot": _flag(data["honeypot"], "honeypot"),
            "quarantine": _flag(data["quarantine"], "quarantine"), "country_block": _flag(data["country_block"], "country_block"),
            "country_threshold": _u32(data["country_threshold"], "country_threshold"),
            "home_countries": _strings(data["home_countries"], "home_countries"),
            "max_actions_per_hour": _u32(data["max_actions_per_hour"], "max_actions_per_hour")}


def alerts_of(raw) -> list[dict]:
    out = []
    for item in raw or []:
        if not isinstance(item, dict):
            raise ValueError("defense.invalid: alert")
        count = item.get("count", 0)
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= U64:
            raise ValueError("defense.invalid: count")
        src, dst = item.get("src", ""), item.get("dst", "")
        if not isinstance(src, str) or not isinstance(dst, str):
            raise ValueError("defense.invalid: address")
        out.append({"kind": _choice(item.get("kind"), KINDS, "kind"), "severity": _choice(item.get("severity"), SEVERITIES, "severity"),
                    "src": src, "dst": dst, "count": count, "at": _number(item.get("at"), "at")})
    return out


def parse(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("defense.invalid")
    now = _number(raw.get("now", 0.0), "now")
    if not math.isfinite(now):
        raise ValueError("defense.invalid: now")
    strikes = raw.get("strikes") or {}
    countries = raw.get("countries") or {}
    if not isinstance(strikes, dict) or not isinstance(countries, dict):
        raise ValueError("defense.invalid")
    return {"now": now, "alerts": alerts_of(raw.get("alerts")), "policy": policy_of(raw.get("policy")),
            "trusted": _strings(raw.get("trusted") or [], "trusted"), "protected": _strings(raw.get("protected") or [], "protected"),
            "active": _strings(raw.get("active") or [], "active"),
            "strikes": {str(k): _u32(v, "strikes") for k, v in strikes.items()},
            "countries": {str(k): v if isinstance(v, str) else _strings([v], "countries")[0] for k, v in countries.items()},
            "recent_actions": _u32(raw.get("recent_actions", 0), "recent_actions")}
