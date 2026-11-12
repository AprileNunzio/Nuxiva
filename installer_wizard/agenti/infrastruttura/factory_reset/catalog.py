from fnmatch import fnmatchcase

DOMAINS = (
    ("people", ("people", "faces", "voiceprints", "ear_*", "wakeword*", "voice_offers.json", "ir_status.json", "habits*")),
    ("memory", ("memoria", "mind", "brain", "study", "skills*", "skill_gaps.json", "router_learning.json", "twin.json",
                "laws", "widget_novelty.json", "understanding*", "wellbeing.db")),
    ("accounts", ("vault*", "telegram.json", "google*", "mcp_*", "music_secret", "authz", "vpn", "tls", "setup_session.json")),
    ("home", ("home", "cameras", "nvr", "webcams.json", "scene.db", "places", "location.json", "printers.json",
              "printer_options.json", "vitals_devices.json", "sounds.json", "sports.json", "maps*", "hardware_master.json")),
    ("automations", ("routines.json", "scheduler.json", "automations*", "projects.json", "whiteboard.json", "ui_templates.json",
                     "widgets*", "flows*", "repair*", "selftest.json", "safe_*", "team_control.json")),
    ("media", ("music*", "tts-cache", "voices", "voicestudio", "models3d", "presentation", "documents*", "locale")),
    ("network", ("nodes.json", "node_enrollment.json", "fleet", "nexus", "packages.json", "srv", "tools", "vendor")),
    ("system", ("state.json", "setup.json", "update_*", "last_good_rev", "local_llm_disabled", "factory_reset.json")),
    ("backups", ("backups",)),
)
OTHER = "other"
KEEP_ETC = frozenset({"nuxiva.env", "core-native.env", "netguard.env"})
KEEP_ENV = frozenset({"NUXIVA_MACHINE", "NUXIVA_HW_PROFILE", "COMPOSE_PROFILES", "NUXIVA_CORE_RUNTIME", "NUXIVA_LLM_MODEL",
                      "NUXIVA_LLM_FAST_MODEL", "NUXIVA_EMBED_MODEL", "NUXIVA_VOICE"})
ROTATE_ENV = frozenset({"NUXIVA_SECRET_KEY", "NUXIVA_VOICESTUDIO_KEY"})
SERVICES = ("nuxiva-supervisor", "nuxiva-ear", "nuxiva-vision", "nuxiva-voice", "nuxiva-core")
SHARE_ROOTS = ("/srv/nuxiva",)


def domain_of(name: str) -> str:
    for domain, patterns in DOMAINS:
        if any(fnmatchcase(name, pattern) for pattern in patterns):
            return domain
    return OTHER


def group(rows: list[dict], log_rows: list[dict], etc_rows: list[dict]) -> list[dict]:
    totals: dict[str, dict] = {}
    for source, items in (("state", rows), ("logs", log_rows), ("etc", etc_rows)):
        for item in items:
            key = {"logs": "logs", "etc": "configuration"}.get(source) or domain_of(item["name"])
            slot = totals.setdefault(key, {"id": key, "items": 0, "files": 0, "bytes": 0})
            slot["items"] += 1
            slot["files"] += item["files"]
            slot["bytes"] += item["bytes"]
    return sorted(totals.values(), key=lambda row: (-row["bytes"], row["id"]))
