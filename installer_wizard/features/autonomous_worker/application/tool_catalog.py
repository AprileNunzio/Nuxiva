import logging
import re
from typing import Any

from features.agent import registry
from features.forge import recipes
from features.autonomous_worker.domain.models import Task
from features.autonomous_worker.domain.sanitizer import sanitize_text, validate_identifier

log = logging.getLogger("nuxiva.autonomous_worker.tool_catalog")

TOOL_CATEGORIES = {
    "system_os": re.compile(r"^(debian_|apt_|service_|power_|ssh_|system_file_|process_|firewall_|run_command|read_file|write_file|make_dir|list_dir|copy|move|delete|zip|find_files|file_info|copy_to_share|share_folder|packages)", re.I),
    "home_automation": re.compile(r"^(ha_|smart_|zigbee|zwave|matter)", re.I),
    "media_tv": re.compile(r"^(tv_|music_|camera_|transcribe_audio|speak_to_file|studio_|avatar|create_3d|show_model)", re.I),
    "whiteboard_math": re.compile(r"^(board_)", re.I),
    "automations_rpa": re.compile(r"^(create_automation|run_automation|toggle_automation|emit_event|schedule_task|cancel_task|run_task_now|rpa_run)", re.I),
    "knowledge_web": re.compile(r"^(web_research|expert_|football_|who_is|person_|red_alert|create_document|create_site|send_email|find_contact)", re.I),
    "fleet_multiagent": re.compile(r"^(fleet_|agent_|ceo_delegate)", re.I),
    "dynamic_forge": re.compile(r"^(create_tool|list_custom_tools|delete_tool|create_widget|delete_widget|create_feature|delete_feature)", re.I),
}

CORE_ALWAYS_AVAILABLE = {
    "read_file",
    "write_file",
    "list_dir",
    "run_command",
    "find_files",
    "web_research",
    "create_tool",
    "emit_event",
    "create_automation",
}


class ToolCatalogManager:
    def __init__(self) -> None:
        self._cached_catalog: list[dict[str, Any]] = []

    def classify_category(self, tool_name: str) -> str:
        for cat, pattern in TOOL_CATEGORIES.items():
            if pattern.search(tool_name):
                return cat
        if tool_name in recipes.CUSTOM:
            return "custom_recipes"
        return "general"

    def scan_all_tools(self, force_refresh: bool = False) -> dict[str, Any]:
        registry.refresh()
        tools_list: list[dict[str, Any]] = []
        categories_count: dict[str, int] = {cat: 0 for cat in TOOL_CATEGORIES}
        categories_count["custom_recipes"] = 0
        categories_count["general"] = 0

        for name, row in sorted(registry.TOOLS.items()):
            cat = self.classify_category(name)
            categories_count[cat] = categories_count.get(cat, 0) + 1

            args_dict = row.get("args")
            args_formatted: dict[str, str] = {}
            if isinstance(args_dict, dict):
                for k, v in args_dict.items():
                    if isinstance(v, dict):
                        args_formatted[str(k)] = str(v.get("type") or v.get("description") or "any")
                    else:
                        args_formatted[str(k)] = str(v)

            is_enabled = registry.enabled(name)
            is_custom = name in recipes.CUSTOM

            tools_list.append({
                "name": name,
                "category": cat,
                "description": str(row.get("description", ""))[:300],
                "args": args_formatted,
                "confirm": bool(row.get("confirm", False)),
                "full_only": bool(row.get("full_only", False)),
                "enabled": is_enabled,
                "source": "custom_recipe" if is_custom else "builtin",
                "agent": str(row.get("agent") or "system"),
            })

        self._cached_catalog = tools_list
        return {
            "total_tools": len(tools_list),
            "enabled_tools": sum(1 for t in tools_list if t["enabled"]),
            "categories": categories_count,
            "tools": tools_list,
        }

    def get_relevant_tools_for_task(self, task: Task, limit: int = 75) -> list[dict[str, Any]]:
        if not self._cached_catalog:
            self.scan_all_tools()

        task_text = f"{task.title} {task.description} {task.specialist_role}".lower()
        scored: list[tuple[int, dict[str, Any]]] = []

        for item in self._cached_catalog:
            if not item["enabled"]:
                continue

            name = item["name"]
            score = 0

            if name in CORE_ALWAYS_AVAILABLE:
                score += 50

            cat = item["category"]
            if cat == "system_os" and any(k in task_text for k in ("file", "cartella", "comando", "shell", "bash", "linux", "debian", "install", "pacchetto", "servizio", "processo")):
                score += 30
            elif cat == "home_automation" and any(k in task_text for k in ("luce", "luci", "home assistant", "casa", "sensore", "entità", "temperatura", "clima")):
                score += 30
            elif cat == "media_tv" and any(k in task_text for k in ("tv", "canale", "musica", "audio", "video", "telecamera", "camera", "voce", "speech")):
                score += 30
            elif cat == "whiteboard_math" and any(k in task_text for k in ("grafico", "formula", "calcolo", "equazione", "whiteboard", "lavagna", "matematica", "fisica")):
                score += 30
            elif cat == "automations_rpa" and any(k in task_text for k in ("automazione", "trigger", "evento", "schedule", "pianifica", "cron", "rpa")):
                score += 30
            elif cat == "knowledge_web" and any(k in task_text for k in ("cerca", "web", "ricerca", "notizia", "informazione", "esperto")):
                score += 30
            elif cat == "fleet_multiagent" and any(k in task_text for k in ("agente", "squadra", "delega", "collabora")):
                score += 30

            words = [w for w in name.split("_") if len(w) > 2]
            for w in words:
                if w in task_text:
                    score += 15

            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    async def study_and_forge_tool(self, spec: dict[str, Any]) -> dict[str, Any]:
        name = validate_identifier(spec.get("name", ""), 40)
        desc = sanitize_text(spec.get("description", ""), 300)
        params = spec.get("params") if isinstance(spec.get("params"), dict) else {}
        steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
        agent_owner = sanitize_text(spec.get("agent", "autonomous_worker"), 40)

        if not name or len(name) < 3:
            raise ValueError("Nome strumento non valido o troppo corto")

        if not steps:
            raise ValueError("Servono passi operativi per forgiare lo strumento")

        saved = recipes.save({
            "name": name,
            "description": desc or f"Strumento sintetizzato da studio autonomo: {name}",
            "params": params,
            "steps": steps,
            "agent": agent_owner,
        })

        self.scan_all_tools(force_refresh=True)
        return {
            "success": True,
            "name": saved["name"],
            "description": saved["description"],
            "steps_count": len(saved["steps"]),
            "agent": saved["agent"],
        }


tool_catalog = ToolCatalogManager()
