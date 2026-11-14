import json
import re

DAY_MS = 86_400_000
HOUR_MS = 3_600_000
MINUTE_MS = 60_000
FADE_MS = 14 * DAY_MS
MAX_PAYLOAD = 1024 * 1024
DOMAINS = ("presence", "schedule", "calendar", "health", "home", "email", "security")
SITUATIONS = ("idle", "conversation", "sleeping", "guests", "meeting")
LEVELS = ("silent", "notify", "propose", "do_and_tell")
RISKS = ("none", "low", "medium", "high")
FORBIDDEN = ("door", "lock", "unlock", "payment", "pay", "delete", "erase", "wipe", "transfer")
IDENT = re.compile(r"^[a-z0-9._:-]{1,128}$")
KIND = re.compile(r"^[a-z0-9._-]{1,32}$")
PRIVACY = ("public", "household", "private")
DEFAULTS = {
    "cost_idle": 100, "cost_conversation": 1000, "cost_sleeping": 900, "cost_guests": 600, "cost_meeting": 800,
    "hourly_cap": 6, "person_hourly_cap": 4, "dedupe_ms": 600_000, "mute_ms": 7 * DAY_MS, "proposal_ttl_ms": HOUR_MS,
    "signal_ttl_ms": 6 * HOUR_MS, "quiet_start_min": 1320, "quiet_end_min": 420, "pending_cap": 64, "log_cap": 512, "deferred_cap": 256,
}


def fail(code: str):
    raise ValueError(f"proactivity.{code}")


def ident(text) -> bool:
    return isinstance(text, str) and IDENT.match(text) is not None


def person_ok(text) -> bool:
    return ident(text) and "|" not in text


def text_ok(text) -> bool:
    return isinstance(text, str) and len(text.encode()) <= 240 and not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in text)


def integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def keys(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= set(obj) or not set(obj) <= set(required) | set(optional):
        return False
    return True


def local(now: int, offset: int):
    offset = max(-840, min(840, offset))
    shifted = max(0, now + offset * MINUTE_MS)
    day = shifted // DAY_MS
    return day, (day + 3) % 7, (shifted % DAY_MS) // MINUTE_MS


def in_span(minute: int, start: int, end: int) -> bool:
    if start == end:
        return False
    return start <= minute < end if start < end else (minute >= start or minute < end)


def forbidden(kind: str) -> bool:
    return any(kind.startswith(p) for p in FORBIDDEN)


def condition_ok(c) -> bool:
    return (keys(c, ("domain", "key", "cmp"), ("threshold", "same_person")) and c["domain"] in DOMAINS and ident(c["key"])
            and c["cmp"] in ("ge", "le", "eq", "present", "absent") and integer(c.get("threshold", 0))
            and -1_000_000 <= c.get("threshold", 0) <= 1_000_000 and isinstance(c.get("same_person", False), bool))


def rule_ok(rid, r) -> bool:
    req = ("domain", "trigger", "audience", "privacy", "urgency", "level", "base_confidence", "min_confidence", "value", "summary_key", "action")
    if not ident(rid) or "|" in rid or not keys(r, req, ("when", "window", "cooldown_ms", "habit")):
        return False
    a = r["action"]
    if not keys(a, ("kind", "class", "priority", "budget", "risk_max", "input_template"), ("scope", "undo")):
        return False
    b = a["budget"]
    if not keys(b, ("wall_ms", "tokens", "tool_calls", "cpu_ms")) or not all(integer(v) and v >= 0 for v in b.values()) or not 1 <= b["wall_ms"] <= DAY_MS:
        return False
    u = a.get("undo")
    if u is not None and not (keys(u, ("kind", "input_template", "window_ms")) and isinstance(u["kind"], str) and KIND.match(u["kind"]) and not forbidden(u["kind"])
                              and len(u["input_template"]) <= 400 and 1 <= u["window_ms"] <= 7 * DAY_MS):
        return False
    w = r.get("window")
    if w is not None and not (keys(w, ("start_min", "end_min"), ("weekdays",)) and 0 <= w["start_min"] < 1440 and 0 <= w["end_min"] < 1440 and 0 < w.get("weekdays", 127) < 128):
        return False
    h = r.get("habit")
    if h is not None and not (keys(h, ("lead_ms", "min_days", "min_permille")) and 0 <= h["lead_ms"] <= 6 * HOUR_MS and 1 <= h["min_days"] <= 365 and 0 <= h["min_permille"] <= 1000):
        return False
    execute_ok = r["level"] != "do_and_tell" or (RISKS.index(a["risk_max"]) <= 1 and u is not None and r["urgency"] == "normal")
    return (r["domain"] in DOMAINS and condition_ok(r["trigger"]) and r["trigger"]["cmp"] != "absent" and isinstance(r.get("when", []), list)
            and len(r.get("when", [])) <= 8 and all(condition_ok(c) for c in r.get("when", [])) and r["audience"] in ("subject", "household")
            and r["privacy"] in PRIVACY and r["urgency"] in ("normal", "critical") and r["level"] in LEVELS
            and all(integer(r[k]) and 0 <= r[k] <= 1000 for k in ("base_confidence", "min_confidence", "value"))
            and ident(r["summary_key"]) and integer(r.get("cooldown_ms", 0)) and 0 <= r.get("cooldown_ms", 0) <= 7 * DAY_MS
            and isinstance(a["kind"], str) and KIND.match(a["kind"]) and not forbidden(a["kind"]) and len(a["input_template"]) <= 400
            and a["class"] in ("voice", "interactive", "background", "maintenance") and a["risk_max"] in RISKS
            and all(ident(s) for s in a.get("scope", [])) and execute_ok)


def load_rules(text: str) -> dict:
    if len(text) > MAX_PAYLOAD:
        fail("too_large")
    try:
        data = json.loads(text)
    except ValueError:
        fail("rules.invalid")
    rules = data.get("rules") if keys(data, ("rules",)) else None
    if not isinstance(rules, dict) or not 1 <= len(rules) <= 1024 or not all(rule_ok(i, r) for i, r in rules.items()):
        fail("rules.invalid")
    return rules


def load_settings(text: str) -> dict:
    if not text:
        return dict(DEFAULTS)
    if len(text) > MAX_PAYLOAD:
        fail("too_large")
    try:
        s = json.loads(text)
    except ValueError:
        fail("settings.invalid")
    if not keys(s, DEFAULTS) or not all(integer(v) and v >= 0 for v in s.values()):
        fail("settings.invalid")
    costs = [s[k] for k in s if k.startswith("cost_")]
    ok = (all(c <= 1000 for c in costs) and s["cost_conversation"] == 1000 and 1 <= s["hourly_cap"] <= 1000 and 1 <= s["person_hourly_cap"] <= s["hourly_cap"]
          and 1 <= s["dedupe_ms"] <= DAY_MS and 1 <= s["mute_ms"] <= 90 * DAY_MS and 1 <= s["proposal_ttl_ms"] <= DAY_MS
          and 1 <= s["signal_ttl_ms"] <= 7 * DAY_MS and s["quiet_start_min"] < 1440 and s["quiet_end_min"] < 1440
          and 1 <= s["pending_cap"] <= 4096 and 1 <= s["log_cap"] <= 65536 and 1 <= s["deferred_cap"] <= 4096)
    if not ok:
        fail("settings.invalid")
    return s


def i32(value) -> bool:
    return integer(value) and -2**31 <= value < 2**31


def u64(value) -> bool:
    return integer(value) and 0 <= value < 2**64


def load_json(text: str, limit: int = 8192):
    if len(text) > limit:
        fail("too_large")
    try:
        return json.loads(text)
    except ValueError:
        fail("parse")


def parse_signal(text: str) -> dict:
    s = load_json(text)
    if not keys(s, ("domain", "key", "at"), ("person", "subject", "value")):
        fail("parse")
    s.setdefault("person", None)
    s.setdefault("subject", "")
    s.setdefault("value", 0)
    ok = (s["domain"] in DOMAINS and isinstance(s["key"], str) and isinstance(s["subject"], str) and i32(s["value"]) and u64(s["at"])
          and (s["person"] is None or isinstance(s["person"], str)))
    if not ok:
        fail("parse")
    return s


def signal_valid(s: dict) -> bool:
    return ident(s["key"]) and text_ok(s["subject"]) and -1_000_000 <= s["value"] <= 1_000_000 and (s["person"] is None or person_ok(s["person"]))


def parse_context(text: str) -> dict:
    c = load_json(text)
    if not keys(c, ("situation",), ("voice_free", "guests_present", "present", "tz_offset_min")):
        fail("parse")
    c.setdefault("voice_free", False)
    c.setdefault("guests_present", False)
    c.setdefault("present", [])
    c.setdefault("tz_offset_min", 0)
    ok = (c["situation"] in SITUATIONS and isinstance(c["voice_free"], bool) and isinstance(c["guests_present"], bool)
          and isinstance(c["present"], list) and all(isinstance(p, str) for p in c["present"]) and i32(c["tz_offset_min"]))
    if not ok:
        fail("parse")
    if not context_valid(c):
        fail("invalid")
    return c


def context_valid(c: dict) -> bool:
    return len(c["present"]) <= 32 and all(person_ok(p) for p in c["present"]) and -840 <= c["tz_offset_min"] <= 840


def parse_forecast(text: str) -> dict:
    f = load_json(text)
    if not keys(f, ("rule", "probability"), ("person", "subject")):
        fail("parse")
    f.setdefault("person", None)
    f.setdefault("subject", "")
    ok = isinstance(f["rule"], str) and isinstance(f["subject"], str) and u32(f["probability"]) and (f["person"] is None or isinstance(f["person"], str))
    if not ok:
        fail("parse")
    return f


def u32(value) -> bool:
    return integer(value) and 0 <= value < 2**32


def forecast_valid(f: dict) -> bool:
    return ident(f["rule"]) and text_ok(f["subject"]) and f["probability"] <= 1000 and (f["person"] is None or person_ok(f["person"]))
