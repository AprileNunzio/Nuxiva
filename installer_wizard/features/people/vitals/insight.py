from features.people.vitals.history import history

SLEEP_GOAL = 480
STEP_GOAL = 8000
KCAL_GOAL = 500
LIMITS = (
    ("spo2", "low", lambda v: v < 92, "warn"),
    ("spo2", "very_low", lambda v: v < 88, "alert"),
    ("heart_rate", "high", lambda v: v > 130, "warn"),
    ("heart_rate", "low", lambda v: v < 40, "warn"),
    ("body_temp", "fever", lambda v: v >= 37.8, "warn"),
    ("body_temp", "high_fever", lambda v: v >= 39.0, "alert"),
    ("bp_sys", "high", lambda v: v >= 140, "warn"),
    ("bp_sys", "very_high", lambda v: v >= 180, "alert"),
    ("bp_dia", "high", lambda v: v >= 90, "warn"),
    ("glucose", "low", lambda v: v < 70, "warn"),
    ("glucose", "high", lambda v: v > 180, "warn"),
    ("resp_rate", "high", lambda v: v > 24, "warn"),
)


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def signals(values: dict) -> list[dict]:
    out, seen = [], set()
    for metric, code, test, level in sorted(LIMITS, key=lambda r: r[3] != "alert"):
        row = values.get(metric)
        if row and metric not in seen and test(float(row["value"])):
            seen.add(metric)
            out.append({"metric": metric, "code": code, "level": level})
    return out[:4]


def recovery(slug: str, values: dict, now: float | None = None) -> dict | None:
    parts = []
    hrv = values.get("hrv")
    base_hrv = history.baseline(slug, "hrv", now)
    if hrv and base_hrv:
        parts.append(("hrv", clamp(70 + (float(hrv["value"]) / base_hrv - 1) * 150), 0.4))
    rest = values.get("resting_hr")
    base_rest = history.baseline(slug, "resting_hr", now)
    if rest and base_rest:
        parts.append(("resting_hr", clamp(70 - (float(rest["value"]) - base_rest) * 6), 0.3))
    sleep = values.get("sleep_min")
    if sleep:
        parts.append(("sleep", clamp(float(sleep["value"]) / SLEEP_GOAL * 100), 0.3))
    if not parts:
        return None
    weight = sum(p[2] for p in parts)
    score = round(sum(p[1] * p[2] for p in parts) / weight)
    return {"score": score, "band": "high" if score >= 70 else "mid" if score >= 45 else "low", "from": [p[0] for p in parts]}


def goals(values: dict) -> dict:
    def ring(metric: str, goal: float) -> dict | None:
        row = values.get(metric)
        return {"value": row["value"], "goal": goal, "pct": round(clamp(float(row["value"]) / goal * 100, 0, 999))} if row else None
    rings = {"steps": ring("steps", STEP_GOAL), "active_kcal": ring("active_kcal", KCAL_GOAL), "sleep_min": ring("sleep_min", SLEEP_GOAL)}
    return {k: v for k, v in rings.items() if v}
