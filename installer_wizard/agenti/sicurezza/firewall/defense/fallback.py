import functools

from agenti.firewall.defense import netaddr
from agenti.firewall.defense.rules import (ASSIST_MINUTES, KINDS, MAX_ACTIONS, MAX_ALERTS, MAX_INCIDENTS, MAX_LIST, MAX_TARGETS,
                                           RECENT, SEVERITIES, SEVERITY_POINTS, STAGE_OF, STAGE_POINTS, STAGES, U32, U64,
                                           fingerprint, level_of, parse, rank, valid_country, window)


def _sev(value: str) -> int:
    return rank(SEVERITIES, value)


def _order(a: dict, b: dict) -> int:
    if a["score"] != b["score"]:
        return -1 if a["score"] > b["score"] else 1
    if a["last_at"] != b["last_at"]:
        return -1 if a["last_at"] > b["last_at"] else 1
    return (a["src"] > b["src"]) - (a["src"] < b["src"])


def correlate(data: dict) -> list[dict]:
    span = window(data["policy"]["window_s"])
    trusted = [n for n in (netaddr.network(t) for t in data["trusted"][:MAX_LIST]) if n is not None]
    protected = {c for c in (netaddr.clean(p) for p in data["protected"][:MAX_LIST]) if c is not None}
    groups: dict[str, dict] = {}
    now = data["now"]
    for alert in data["alerts"][:MAX_ALERTS]:
        at = alert["at"]
        if at != at or at in (float("inf"), float("-inf")) or now - at > span or at > now + 60.0:
            continue
        src = netaddr.clean(alert["src"])
        if src is None:
            continue
        acc = groups.setdefault(src, {"kinds": set(), "severity": None, "alerts": 0, "events": 0, "targets": set(),
                                      "first_at": at, "last_at": at})
        acc["kinds"].add(alert["kind"])
        acc["severity"] = alert["severity"] if acc["severity"] is None else max(acc["severity"], alert["severity"], key=_sev)
        acc["alerts"] = min(acc["alerts"] + 1, U32)
        acc["events"] = min(acc["events"] + max(alert["count"], 1), U64)
        acc["first_at"] = min(acc["first_at"], at)
        acc["last_at"] = max(acc["last_at"], at)
        if len(acc["targets"]) < MAX_TARGETS:
            dst = netaddr.clean(alert["dst"])
            if dst is not None:
                acc["targets"].add(dst)
    out = [_build(data, trusted, protected, src, groups[src]) for src in sorted(groups)]
    out.sort(key=functools.cmp_to_key(_order))
    return out[:MAX_INCIDENTS]


def _build(data: dict, trusted: list, protected: set, src: str, acc: dict) -> dict:
    addr = netaddr.address(src)
    origin = "internet" if addr is not None and not netaddr.is_lan(addr) else "lan"
    country = (valid_country(data["countries"].get(src)) or "") if origin == "internet" else ""
    kinds = sorted(acc["kinds"], key=KINDS.index)
    stages = sorted({STAGE_OF[k] for k in kinds}, key=lambda s: rank(STAGES, s))
    stage = stages[-1] if stages else "recon"
    severity = acc["severity"] or "low"
    strikes = min(data["strikes"].get(src, 0), 1000)
    score = min(SEVERITY_POINTS[severity] + (len(kinds) - 1) * 6 + min(acc["alerts"], 15) + STAGE_POINTS[stage]
                + min(strikes * 5, 20), 100)
    return {"id": fingerprint(src), "src": src, "origin": origin, "country": country, "kinds": kinds, "stage": stage,
            "stages": stages, "severity": severity, "level": level_of(score), "score": score, "alerts": acc["alerts"],
            "events": acc["events"], "targets": sorted(acc["targets"]), "first_at": acc["first_at"], "last_at": acc["last_at"],
            "trusted": addr is not None and any(netaddr.contains(t, addr) for t in trusted), "protected": src in protected,
            "strikes": strikes}


def _choose(incident: dict, policy: dict) -> tuple[str, str]:
    if incident["protected"]:
        return "warn", "protected_source"
    if incident["trusted"]:
        return "warn", "trusted_anomaly"
    stage, level = rank(STAGES, incident["stage"]), _sev(incident["level"])
    if incident["origin"] == "lan":
        if stage >= rank(STAGES, "interception") and level >= _sev("high") and policy["quarantine"]:
            return "quarantine", "lan_compromise"
        return "warn", "lan_anomaly"
    name = incident["stage"]
    if name == "recon":
        if policy["honeypot"]:
            return "honeypot", "recon_deception"
        return ("tarpit", "recon_slowdown") if policy["tarpit"] else ("block", "recon_block")
    if name == "disruption":
        return ("rate_limit", "flood_limit") if level < _sev("critical") else ("block", "flood_block")
    if name == "exfiltration":
        return "block", "exfiltration_block"
    return "block", "intrusion_block"


def duration(policy: dict, strikes: int) -> int:
    ceiling = min(max(policy["max_minutes"], 1), 525_600)
    base = min(max(policy["block_minutes"], 1), ceiling)
    return min(base * (1 << min(strikes, 10)), U32, ceiling)


def _allowed(autonomy: str, kind: str, minutes: int) -> bool:
    if autonomy == "observe":
        return False
    if autonomy == "assist":
        return minutes <= ASSIST_MINUTES and kind in ("sinkhole", "rate_limit", "tarpit", "honeypot", "block")
    return True


def plan(data: dict, incidents: list[dict]) -> list[dict]:
    policy = data["policy"]
    enforcing = policy["mode"] in ("protect", "lockdown")
    active = {c for c in (netaddr.clean(a) for a in data["active"][:MAX_LIST]) if c is not None}
    protected = {c for c in (netaddr.clean(a) for a in data["protected"][:MAX_LIST]) if c is not None}
    budget = max(policy["max_actions_per_hour"] - data["recent_actions"], 0)
    used = 0
    actions = []
    for incident in incidents:
        if _sev(incident["level"]) < _sev(policy["min_level"]):
            continue
        kind, reason = _choose(incident, policy)
        if kind == "warn" or incident["src"] not in active:
            minutes = 0 if kind == "warn" else duration(policy, incident["strikes"])
            auto = enforcing and kind != "warn" and _allowed(policy["autonomy"], kind, minutes) and used < budget
            used += 1 if auto else 0
            actions.append({"kind": kind, "target": incident["src"], "minutes": minutes, "reason": reason,
                            "incident": incident["id"], "auto": auto, "reversible": True})
        if incident["origin"] != "lan" or incident["stage"] != "exfiltration" or incident["protected"]:
            continue
        for target in incident["targets"]:
            found = netaddr.ip(target)
            if found is None or netaddr.is_lan(("ip", found)) or target in active or target in protected:
                continue
            minutes = duration(policy, incident["strikes"])
            auto = enforcing and _allowed(policy["autonomy"], "sinkhole", minutes) and used < budget
            used += 1 if auto else 0
            actions.append({"kind": "sinkhole", "target": target, "minutes": minutes, "reason": "exfiltration_sinkhole",
                            "incident": incident["id"], "auto": auto, "reversible": True})
    if policy["country_block"]:
        home = {"".join(c.upper() if "a" <= c <= "z" else c for c in h.strip()) for h in policy["home_countries"]}
        threshold = max(policy["country_threshold"], 2)
        waves: dict[str, int] = {}
        for incident in incidents:
            if (incident["origin"] == "internet" and incident["country"] and _sev(incident["level"]) >= _sev("medium")
                    and not incident["trusted"] and not incident["protected"]):
                waves[incident["country"]] = waves.get(incident["country"], 0) + 1
        for country in sorted(waves):
            target = f"country:{country}"
            if waves[country] < threshold or country in home or target in active:
                continue
            auto = enforcing and policy["autonomy"] == "autonomous" and used < budget
            used += 1 if auto else 0
            actions.append({"kind": "country_block", "target": target,
                            "minutes": min(max(policy["block_minutes"], 60), min(max(policy["max_minutes"], 60), 525_600)),
                            "reason": "country_wave", "incident": "", "auto": auto, "reversible": True})
    return actions[:MAX_ACTIONS]


def countries(incidents: list[dict]) -> list[dict]:
    found: dict[str, list] = {}
    for incident in incidents:
        if incident["origin"] != "internet" or not incident["country"]:
            continue
        slot = found.setdefault(incident["country"], [0, "low"])
        slot[0] += 1
        slot[1] = max(slot[1], incident["level"], key=_sev)
    out = [{"country": c, "incidents": n, "level": lv} for c, (n, lv) in sorted(found.items())]
    out.sort(key=lambda c: (-c["incidents"], c["country"]))
    return out


def posture(now: float, incidents: list[dict]) -> str:
    levels = [_sev(i["level"]) for i in incidents if now - i["last_at"] <= RECENT]
    if not levels:
        return "calm"
    top = max(levels)
    return "watch" if top <= 1 else "alert" if top == 2 else "attack"


def assess(raw: dict) -> dict:
    data = parse(raw)
    incidents = correlate(data)
    lan = sum(1 for i in incidents if i["origin"] == "lan")
    return {"posture": posture(data["now"], incidents), "incidents": incidents, "actions": plan(data, incidents),
            "countries": countries(incidents), "internet": len(incidents) - lan, "lan": lan}
