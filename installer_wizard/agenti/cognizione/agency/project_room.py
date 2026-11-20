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


def _create_pc_workstation(index: int, agent_id: str | None, is_called: bool, kind: str, slot: str = "primary") -> dict[str, Any]:
    hostname = f"ws-{agent_id or 'spare'}-{index:02d}"
    screen_count = 2 if kind in ("double", "pair_collaborative") else 1
    status = "active" if is_called else "standby"
    return {
        "pc_id": f"pc_{index:03d}_{slot}" if slot != "primary" else f"pc_{index:03d}",
        "hostname": hostname,
        "screen_count": screen_count,
        "screens_resolution": "4K Ultra-Wide" if screen_count > 1 else "1440p Retina",
        "status": status,
        "glow_color": "#0ea5e9" if is_called else "#334155",
        "assigned_worker": agent_id,
        "os": "Nuxiva OS 2026.4",
        "network_ip": f"10.244.1.{10 + (index % 200)}",
        "gpu_acceleration": True,
        "active_stream": is_called,
    }


def assign_pair_to_desk(desk: dict[str, Any], second_role: str) -> dict[str, Any]:
    idx = desk.get("index", 0)
    pc2 = _create_pc_workstation(idx + 100, second_role, True, "pair_collaborative", slot="secondary")
    desk["second_agent_id"] = second_role
    agents_list = [desk.get("agent_id")] if desk.get("agent_id") else []
    if second_role not in agents_list:
        agents_list.append(second_role)
    desk["agents"] = agents_list
    desk["is_pair_programming"] = True
    desk["collaboration_mode"] = "pair_programming"
    desk["kind"] = "pair_collaborative"
    desk["capacity"] = 2
    desk["seat"] = "dual_shared"
    desk["pc_secondary"] = pc2
    w_list = list(desk.get("workstations") or ([desk.get("workstation")] if desk.get("workstation") else []))
    if not any(w.get("pc_id") == pc2["pc_id"] for w in w_list):
        w_list.append(pc2)
    desk["workstations"] = w_list
    desk["shared_screen"] = {"enabled": True, "sync_stream": "dual_mirror", "pair_mode": True}
    return desk


def generate_autonomous_desks_and_pcs(called_roles: list[Any], pair_programming: bool = False) -> list[dict[str, Any]]:
    norm_slots: list[tuple[str | None, str | None]] = []
    if pair_programming and called_roles:
        flat = []
        for item in called_roles:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                norm_slots.append((str(item[0]), str(item[1])))
            elif isinstance(item, (list, tuple)) and len(item) == 1:
                flat.append(str(item[0]))
            elif item is not None:
                flat.append(str(item))
        for i in range(0, len(flat), 2):
            r1 = flat[i]
            r2 = flat[i + 1] if i + 1 < len(flat) else None
            norm_slots.append((r1, r2))
    else:
        for item in called_roles:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                norm_slots.append((str(item[0]), str(item[1])))
            elif isinstance(item, (list, tuple)) and len(item) == 1:
                norm_slots.append((str(item[0]), None))
            elif item is not None:
                norm_slots.append((str(item), None))
            else:
                norm_slots.append((None, None))

    count = max(len(norm_slots), 4)
    desks: list[dict[str, Any]] = []

    for idx in range(count):
        row = idx // 4
        col = idx % 4
        x = round(-2.4 + col * 1.6, 2)
        z = round(-0.6 + row * 1.8, 2)

        slot = norm_slots[idx] if idx < len(norm_slots) else (None, None)
        r1, r2 = slot
        is_occupied = r1 is not None or r2 is not None
        is_pair = r1 is not None and r2 is not None
        kind = "pair_collaborative" if is_pair else ("double" if row == 0 else "single")
        seat = "dual_shared" if is_pair else ("center" if kind == "single" else ("left" if col % 2 == 0 else "right"))

        pc1 = _create_pc_workstation(idx, r1, r1 is not None, kind, slot="primary")
        zone_label = "Reparto Operativo Core" if row == 0 else f"Reparto Specializzato {row + 1}"
        desk = {
            "index": idx,
            "kind": kind,
            "capacity": 2 if (kind in ("double", "pair_collaborative")) else 1,
            "seat": seat,
            "x": x,
            "z": z,
            "zone": zone_label,
            "occupied": is_occupied,
            "agent_id": r1,
            "second_agent_id": r2,
            "agents": [r for r in (r1, r2) if r is not None],
            "is_pair_programming": is_pair,
            "collaboration_mode": "pair_programming" if is_pair else ("solo" if r1 else "idle"),
            "workstation": pc1,
            "pc": pc1,
            "workstations": [pc1],
        }
        if r2 is not None:
            assign_pair_to_desk(desk, r2)
        desks.append(desk)
    return desks


def build_project_room(data: dict, base: dict, agents: list[dict], ceo: dict, shared_brain: dict) -> dict[str, Any]:
    project = data.get("project") or {}
    project_id = str(project.get("id") or base.get("id") or "main_project").strip()
    title = clean(project.get("title") or base.get("title") or "Progetto Principale", 120)
    goal = clean(base.get("goal") or project.get("goal") or "", 300)
    status = str(base.get("status") or project.get("status") or "running")

    called_agents = [a for a in agents if a.get("seated") or a.get("status") in ("running", "review", "pending")]
    called_role_ids = [str(a.get("role") or a.get("id")) for a in called_agents]

    pair_req = bool(data.get("pair_programming") or base.get("pair_programming"))
    desks = generate_autonomous_desks_and_pcs(called_role_ids, pair_programming=pair_req)
    dims = _calculate_room_dimensions(len(desks))
    theme = _resolve_room_theme(goal, title)

    room_id = f"room_{project_id.replace('-', '_')}"
    workstations = []
    for d in desks:
        workstations.extend(d.get("workstations", [d["workstation"]]))

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
        "pair_programming_desks_count": sum(1 for d in desks if d.get("is_pair_programming")),
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
