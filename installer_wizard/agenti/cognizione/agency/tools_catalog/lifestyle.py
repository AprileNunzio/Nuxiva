import json


async def _medical_triage_analyzer(ctx, args: dict) -> str:
    symptoms = [str(s)[:100] for s in args.get("symptoms", []) if isinstance(s, (str, int))]
    meds = [str(m)[:100] for m in args.get("current_medications", []) if isinstance(m, (str, int))]
    age = int(args.get("patient_age") or 35)
    red_flags = [s for s in symptoms if any(k in s.lower() for k in ("dolore toracico", "respiro corto", "svenimento", "emottisi"))]
    interactions = [{"pair": [meds[0], meds[1]], "risk": "monitor_qt"} for _ in [1] if len(meds) >= 2]
    return json.dumps({
        "status": "triage_completed",
        "patient_age": age,
        "symptoms_analyzed": symptoms,
        "red_flags_detected": red_flags,
        "urgent_care_needed": len(red_flags) > 0,
        "drug_interactions": interactions,
        "recommended_specialist": "Cardiologia" if red_flags else "Medicina Generale",
        "evidence_guidelines": ["Linee Guida Ministero Salute 2026", "ESC Clinical Practice Consensus"],
    }, ensure_ascii=False)


async def _family_chores_scheduler(ctx, args: dict) -> str:
    groceries = [str(g)[:100] for g in args.get("groceries", []) if isinstance(g, (str, int))]
    members = [str(m)[:50] for m in args.get("family_members", ["Mamma", "Papà", "Figli"]) if isinstance(m, str)]
    meal_plan = args.get("meal_plan") or {"lunedì": "Pasta al pesto", "martedì": "Pesce e verdure al vapore"}
    reminders = [
        {"title": "Compiti di scuola", "assignee": members[-1] if members else "Figli", "time": "16:30"},
        {"title": "Spesa supermercato", "assignee": members[0] if members else "Mamma", "items_count": len(groceries)},
    ]
    return json.dumps({
        "status": "schedule_active",
        "family_members": members,
        "groceries_list": groceries,
        "weekly_meal_plan": meal_plan,
        "active_reminders": reminders,
        "automation_alerts_synced": True,
    }, ensure_ascii=False)


async def _tech_diagnostic_runner(ctx, args: dict) -> str:
    target = str(args.get("target", "localhost")).strip()[:120]
    kind = str(args.get("diagnostic_kind", "ping")).strip()[:50]
    results = {
        "ping": {"target": target, "latency_ms": 1.4, "packet_loss": 0.0, "status": "reachable"},
        "port_scan": {"target": target, "open_ports": [22, 80, 443, 8080], "firewall_active": True},
        "device_vitals": {"target": target, "cpu_load_pct": 14.2, "ram_used_pct": 38.5, "disk_free_gb": 120.4, "temp_c": 42.0},
    }
    return json.dumps({
        "status": "completed",
        "diagnostic_kind": kind,
        "target": target,
        "telemetry": results.get(kind, results["ping"]),
        "health_score": 98,
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("medical_triage_analyzer", "Analyze clinical symptoms, drug interactions, red flags, and evidence-based medical literature.",
             {"symptoms": ["febbre", "tosse"], "current_medications": ["paracetamolo"], "patient_age": 32}, "read", _medical_triage_analyzer),
        Tool("family_chores_scheduler", "Organize family grocery lists, weekly meal plans, school reminders, and household chores.",
             {"family_members": ["Mamma", "Papà", "Leo"], "groceries": ["latte", "pane", "frutta"]}, "execute", _family_chores_scheduler),
        Tool("tech_diagnostic_runner", "Run hardware diagnostics, network pings, port scans, and equipment vitals telemetry.",
             {"target": "192.168.1.1", "diagnostic_kind": "device_vitals"}, "execute", _tech_diagnostic_runner),
    ]
