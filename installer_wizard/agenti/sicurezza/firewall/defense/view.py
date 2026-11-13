import time

MAX_INCIDENTS = 5
MAX_DEFENSES = 6


def _incident(row: dict) -> dict:
    return {"id": row["id"], "kind": row["kinds"][0] if row["kinds"] else "", "kinds": row["kinds"][:4], "stage": row["stage"],
            "level": row["level"], "country": row["country"], "origin": row["origin"], "src": row["src"][:64],
            "targets": len(row["targets"]), "last_at": row["last_at"]}


def _defense(row: dict) -> dict:
    return {"kind": row["kind"], "target": row["target"], "expires": row["expires"], "auto": row["auto"]}


def build() -> dict:
    from agenti.firewall.defense.guardian import guardian
    from agenti.firewall.store import store
    state = guardian.assessment
    with store.lock:
        mode, autonomy = store.policy.mode, store.policy.autonomy
        trusted = len(store.policy.trusted)
        defenses = [_defense(r.export()) for r in sorted(store.responses.values(), key=lambda r: r.expires)][:MAX_DEFENSES]
    return {"posture": state.get("posture", "calm"), "mode": mode, "autonomy": autonomy, "trusted": trusted,
            "incidents": [_incident(i) for i in state.get("incidents", [])[:MAX_INCIDENTS]], "defenses": defenses,
            "internet": state.get("internet", 0), "lan": state.get("lan", 0), "at": state.get("at", 0.0) or time.time()}


def notable() -> dict | None:
    data = build()
    return data if data["posture"] != "calm" or data["defenses"] else None
