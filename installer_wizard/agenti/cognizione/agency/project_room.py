import math
from typing import Any

from agenti.agency.text import clean

DEFAULT_ROOM_THEMES = {
    "tech": "cyber_minimal_glass",
    "creative": "studio_creative_warm",
    "finance": "fintech_war_room",
    "education": "socratic_academy_lab",
    "default": "minimal_isometric_3d",
}

_PROJECT_ROOMS: dict[str, dict[str, Any]] = {}


def _resolve_room_theme(goal: str, title: str) -> str:
    target = f"{title} {goal}".lower()
    if any(k in target for k in ("finanz", "bors", "mercato", "crypto", "trading", "fisco")):
        return DEFAULT_ROOM_THEMES["finance"]
    if any(k in target for k in ("scuola", "compit", "studio", "lezion", "tutor", "formazion")):
        return DEFAULT_ROOM_THEMES["education"]
    if any(k in target for k in ("design", "grafica", "video", "arte", "musica", "marketing")):
        return DEFAULT_ROOM_THEMES["creative"]
    if any(k in target for k in ("codice", "sviluppo", "server", "api", "ai", "cloud", "software")):
        return DEFAULT_ROOM_THEMES["tech"]
    return DEFAULT_ROOM_THEMES["default"]


def _calculate_room_dimensions(total_desks: int) -> dict[str, float]:
    rows = max(1, math.ceil(total_desks / 4))
    width = round(max(12.4, 6.2 + (total_desks // 4) * 2.2), 2)
    depth = round(max(8.4, 4.4 + rows * 1.5), 2)
    height = 3.8
    area = round(width * depth, 2)
    return {
        "width": width,
        "depth": depth,
        "height": height,
        "floor_area_sqm": area,
    }


def _create_pc_workstation(index: int, agent_id: str | None, is_called: bool, kind: str) -> dict[str, Any]:
    hostname = f"ws-{agent_id or 'spare'}-{index:02d}"
    screen_count = 2 if kind == "double" else 1
    status = "active" if is_called else "standby"
    return {
        "pc_id": f"pc_{index:03d}",
        "hostname": hostname,
        "screen_count": screen_count,
        "screens_resolution": "4K Ultra-Wide" if screen_count > 1 else "1440p Retina",
        "status": status,
        "glow_color": "#0ea5e9" if is_called else "#334155",
        "assigned_worker": agent_id,
        "os": "Nuxiva OS 2026.4",
        "network_ip": f"10.244.1.{10 + index}",
        "gpu_acceleration": True,
        "active_stream": is_called,
    }


def generate_autonomous_desks_and_pcs(called_roles: list[str]) -> list[dict[str, Any]]:
    count = max(len(called_roles), 4)
    desks: list[dict[str, Any]] = []

    for idx in range(count):
        row = idx // 4
        col = idx % 4
        x = round(-2.4 + col * 1.6, 2)
        z = round(-0.6 + row * 1.8, 2)

        assigned_role = called_roles[idx] if idx < len(called_roles) else None
        is_occupied = assigned_role is not None
        kind = "double" if row == 0 else "single"
        seat = "center" if kind == "single" else ("left" if col % 2 == 0 else "right")

        pc = _create_pc_workstation(idx, assigned_role, is_occupied, kind)

        zone_label = "Reparto Operativo Core" if row == 0 else f"Reparto Specializzato {row + 1}"
        desks.append({
            "index": idx,
            "kind": kind,
            "seat": seat,
            "x": x,
            "z": z,
            "zone": zone_label,
            "occupied": is_occupied,
            "agent_id": assigned_role,
            "workstation": pc,
            "pc": pc,
        })
    return desks


def build_project_room(data: dict, base: dict, agents: list[dict], ceo: dict, shared_brain: dict) -> dict[str, Any]:
    project = data.get("project") or {}
    project_id = str(project.get("id") or base.get("id") or "main_project").strip()
    title = clean(project.get("title") or base.get("title") or "Progetto Principale", 120)
    goal = clean(base.get("goal") or project.get("goal") or "", 300)
    status = str(base.get("status") or project.get("status") or "running")

    called_agents = [a for a in agents if a.get("seated") or a.get("status") in ("running", "review", "pending")]
    called_role_ids = [str(a.get("role") or a.get("id")) for a in called_agents]

    desks = generate_autonomous_desks_and_pcs(called_role_ids)
    dims = _calculate_room_dimensions(len(desks))
    theme = _resolve_room_theme(goal, title)

    room_id = f"room_{project_id.replace('-', '_')}"
    workstations = [d["workstation"] for d in desks]

    room = {
        "room_id": room_id,
        "project_id": project_id,
        "name": f"Stanza Progetto: {title}",
        "title": title,
        "goal": goal,
        "status": status,
        "theme": theme,
        "type": "autonomous_project_workroom",
        "dimensions": dims,
        "desks_count": len(desks),
        "active_workers_count": len(called_agents),
        "desks": desks,
        "workstations": workstations,
        "seated_agents": called_agents,
        "ceo_podium": {
            "x": 0.0,
            "z": -3.2,
            "ceo_id": ceo.get("id", "ceo"),
            "status": ceo.get("status", "running"),
        },
        "shared_brain_core": {
            "x": 0.0,
            "z": -1.78,
            "rules_count": shared_brain.get("rules_count", 1687),
            "reviews_count": shared_brain.get("reviews_count", 943),
        },
        "ambient": {
            "lighting": "daylight_adaptive_led",
            "soundscape": "low_hum_productivity",
            "holographic_field": "active_coherent",
            "air_quality_index": 98,
        },
    }

    _PROJECT_ROOMS[project_id] = room
    return room


def get_project_room(project_id: str) -> dict[str, Any] | None:
    return _PROJECT_ROOMS.get(project_id)


def list_project_rooms() -> list[dict[str, Any]]:
    return list(_PROJECT_ROOMS.values())
