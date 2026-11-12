from agenti.authz import risk as risks
from agenti.authz.capability import EntityLookup, HA_READ_PRIVATE, domain_of, entity_ids
from agenti.home_assistant.nlu.vocabulary import SENSITIVE_COVERS

COMFORT_RANGE = (18.0, 24.0)
APPLIANCES = frozenset({"switch", "input_boolean", "button", "number", "select", "input_number", "input_select",
                        "vacuum", "siren"})
CLIMATE = frozenset({"climate", "water_heater", "humidifier"})
GATE_OPEN = frozenset({"open_cover", "set_cover_position", "toggle", "stop_cover"})

TOOL_CAPS: dict[str, str] = {
    **dict.fromkeys(("music_play", "music_control"), "media.music.play"),
    **dict.fromkeys(("tv_play_channel",), "media.tv.watch"),
    **dict.fromkeys(("tv_add_tuner", "tv_set_vpn_policy", "tv_scan_tuner"), "media.tv.manage"),
    **dict.fromkeys(("show_widget", "hide_widget", "move_widget"), "display.widget.show"),
    **dict.fromkeys(("ha_list_entities", "ha_ask_assist"), "home.private.read"),
    **dict.fromkeys(("ha_devices_by_room", "ha_energy_consumption"), "home.state.read"),
    **dict.fromkeys(("run_automation", "toggle_automation", "emit_event"), "home.automation.run"),
    **dict.fromkeys(("create_automation",), "home.automation.edit"),
    **dict.fromkeys(("who_is", "person_profile", "person_mood", "find_contact"), "people.profile.read"),
    **dict.fromkeys(("person_learn",), "people.profile.edit"),
    **dict.fromkeys(("camera_events", "camera_overview", "list_cameras", "open_camera", "camera_photo",
                     "camsense_list", "camsense_state", "camsense_learn"), "home.camera.view"),
    **dict.fromkeys(("camera_motion", "camsense_create"), "home.camera.manage"),
    **dict.fromkeys(("send_email", "share_folder"), "comm.message.send"),
    **dict.fromkeys(("read_file", "list_dir", "find_files", "file_info", "transcribe_audio"), "files.document.read"),
    **dict.fromkeys(("write_file", "make_dir", "copy", "move", "zip", "create_document", "copy_to_share",
                     "create_site", "create_3d", "speak_to_file"), "files.document.write"),
    **dict.fromkeys(("delete",), "files.document.delete"),
    **dict.fromkeys(("firewall_status", "vpn_status", "proxmox_status", "debian_status", "debian_logs",
                     "debian_processes", "debian_network", "ssh_public_key", "system_file_read"), "system.status.read"),
    **dict.fromkeys(("firewall_block", "firewall_unblock", "vpn_connect", "vpn_disconnect", "proxmox_power",
                     "debian_service", "apt_install", "apt_remove", "apt_maintain", "service_control", "power_control",
                     "ssh_exec", "debian_shell", "process_kill", "system_file_write", "packages", "run_command",
                     "rpa_run", "http_get", "schedule_task", "cancel_task", "run_task_now", "agent_set", "dev_run"),
                    "system.admin.manage"),
    **dict.fromkeys(("brain_assign_agent_model", "brain_assign_device_model"), "brain.model.manage"),
    **dict.fromkeys(("create_tool", "delete_tool", "create_feature", "delete_feature", "create_widget",
                     "delete_widget"), "system.feature.create"),
    **dict.fromkeys(("agent_tell", "ceo_delegate", "dev_new", "dev_write", "dev_plan", "dev_build", "dev_publish",
                     "fleet_create", "fleet_attach", "fleet_retire", "expert_create"), "agency.project.manage"),
}


def _temperature(data: dict) -> float | None:
    try:
        return float(data.get("temperature"))
    except (TypeError, ValueError, OverflowError):
        return None


def ha_capability(domain: str, service: str, entity: dict, data: dict) -> str:
    if domain == "light":
        return "home.light.set"
    if domain in ("fan",):
        return "home.comfort.set"
    if domain in ("media_player", "remote"):
        return "media.tv.watch"
    if domain == "scene":
        return "home.scene.activate"
    if domain == "cover":
        if entity.get("device_class") in SENSITIVE_COVERS:
            return "home.gate.open" if service in GATE_OPEN else "home.gate.close"
        return "home.cover.set"
    if domain == "lock":
        return "home.lock.lock" if service == "lock" else "home.lock.unlock"
    if domain == "alarm_control_panel":
        return "home.alarm.arm" if service.startswith("alarm_arm") else "home.alarm.disarm"
    if domain in CLIMATE:
        value = _temperature(data)
        comfy = service == "set_temperature" and value is not None and COMFORT_RANGE[0] <= value <= COMFORT_RANGE[1]
        return "home.climate.adjust" if comfy else "home.climate.set"
    if domain == "valve":
        return "home.valve.set"
    if domain in APPLIANCES:
        return "home.appliance.set"
    if domain == "camera":
        return "home.camera.manage"
    if domain in ("automation", "script"):
        return "home.automation.run"
    if domain == "homeassistant":
        return "home.system.manage"
    return "risk.critical"


def ha_service(args: dict, lookup: EntityLookup) -> list[str]:
    from agenti.authz import capability
    rules = capability.native_rules()
    if rules is None:
        return _py_ha_service(args, lookup)
    data = args.get("data") if isinstance(args.get("data"), dict) else args
    service, declared, targets = capability.call_targets(args, lookup)
    pairs = [(domain, capability.device_class(entity)) for domain, entity in targets]
    return list(rules.call_capabilities(declared, service, pairs, _temperature(data)))


def _py_ha_service(args: dict, lookup: EntityLookup) -> list[str]:
    service = str(args.get("service") or "").strip().lower()
    declared = str(args.get("domain") or "").strip().lower()
    data = args.get("data") if isinstance(args.get("data"), dict) else args
    ids = entity_ids(args.get("entity_id"))
    targets = [(domain_of(eid) or declared, lookup(eid) or {}) for eid in ids] or [(declared, {})]
    caps = [ha_capability(domain, service, entity, data) for domain, entity in targets]
    if declared and declared not in {domain for domain, _ in targets}:
        caps.append(ha_capability(declared, service, {}, data))
    return sorted(set(caps))


def ha_read(args: dict) -> list[str]:
    from agenti.authz import capability
    rules = capability.native_rules()
    if rules is None:
        return _py_ha_read(args)
    return [rules.read_capability([domain_of(eid) for eid in entity_ids(args.get("entity_id"))])]


def _py_ha_read(args: dict) -> list[str]:
    private = any(domain_of(eid) in HA_READ_PRIVATE for eid in entity_ids(args.get("entity_id")))
    return ["home.private.read" if private else "home.state.read"]


def of_call(name: str, args) -> list[str]:
    given = args if isinstance(args, dict) else {}
    if name == "ha_call_service":
        return ha_service(given, _lookup())
    if name == "ha_get_state":
        return ha_read(given)
    if name in TOOL_CAPS:
        return [TOOL_CAPS[name]]
    return [f"risk.{risks.of_tool(name).name.lower()}"]


def of_plan(plan: dict, lookup: EntityLookup) -> list[str]:
    caps: set[str] = set()
    for call in plan.get("calls") or []:
        if isinstance(call, dict):
            caps.update(ha_service({"domain": call.get("domain"), "service": call.get("service"),
                                    "entity_id": call.get("entity_ids") or [], "data": call.get("data") or {}}, lookup))
    if plan.get("kind") == "query":
        caps.update(ha_read({"entity_id": plan.get("entities") or []}))
    return sorted(caps) or ["info.general.read"]


def _lookup() -> EntityLookup:
    from agenti.authz import capability
    return capability.ha_lookup
