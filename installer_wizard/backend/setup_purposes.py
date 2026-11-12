from dataclasses import dataclass

from setup_config import WIZARD_PACKAGES

PURPOSES = {
    "home": {"enable": ("NUXIVA_AUTOMATIONS", "NUXIVA_HABITS", "NUXIVA_TWIN"), "packages": ("voice",),
             "consents": ("listening", "voiceprint", "cameras", "location")},
    "security": {"enable": ("NUXIVA_REDALERT", "NUXIVA_AUTOMATIONS"), "packages": (),
                 "consents": ("cameras", "faces", "network_guard", "listening", "voiceprint")},
    "work": {"enable": ("NUXIVA_AGENCY", "NUXIVA_SKILLS", "NUXIVA_FLEET", "NUXIVA_EXPERTS"), "packages": ("documents",),
             "consents": ("code_run", "web_research", "auto_experts")},
    "family": {"enable": ("NUXIVA_MUSIC_ID", "NUXIVA_GAMES", "NUXIVA_SPORTS"), "packages": ("voice",),
               "consents": ("listening", "voiceprint", "location", "faces")},
    "knowledge": {"enable": ("NUXIVA_SKILLS", "NUXIVA_EXPERTS", "NUXIVA_FLEET"), "packages": ("documents",),
                  "consents": ("web_research", "auto_experts")},
}

CONSENTS = {
    "faces": {"on": {"NUXIVA_VISION": "1"}, "off": {"NUXIVA_VISION": "0"}, "package": "vision"},
    "listening": {"on": {"NUXIVA_EAR": "1"}, "off": {"NUXIVA_EAR": "0"}, "package": "ear"},
    "voiceprint": {"on": {"NUXIVA_VOICEPRINT_ENFORCE": "1"}, "off": {"NUXIVA_VOICEPRINT_ENFORCE": "0"}},
    "cameras": {"on": {"NUXIVA_CAMERAS": "1"}, "off": {"NUXIVA_CAMERAS": "0"}},
    "web_research": {"on": {"NUXIVA_RESEARCH": "1"}, "off": {"NUXIVA_RESEARCH": "0"}},
    "location": {"on": {"NUXIVA_LOCATION_MODE": "auto"}, "off": {"NUXIVA_LOCATION_MODE": "fixed"}},
    "code_run": {"on": {"NUXIVA_DEVSTUDIO": "1"}, "off": {"NUXIVA_DEVSTUDIO": "0"}},
    "auto_experts": {"on": {"NUXIVA_EXPERTS_AUTO": "1"}, "off": {"NUXIVA_EXPERTS_AUTO": "0"}},
    "network_guard": {"on": {"NUXIVA_NETGUARD": "1"}, "off": {"NUXIVA_NETGUARD": "0"}},
}


@dataclass(frozen=True)
class Plan:
    purposes: tuple[str, ...]
    asked: tuple[str, ...]
    pending: tuple[str, ...]
    updates: dict
    packages: tuple[str, ...]
    denied: tuple[str, ...]
    included: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"purposes": list(self.purposes), "asked": list(self.asked), "pending": list(self.pending), "updates": dict(self.updates),
                "packages": list(self.packages), "denied": list(self.denied), "included": list(self.included)}


class PlanError(ValueError):
    pass


def _ordered(items) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def describe() -> dict:
    return {"purposes": {pid: {"packages": list(spec["packages"]), "consents": list(spec["consents"]), "enable": list(spec["enable"])}
                         for pid, spec in PURPOSES.items()},
            "consents": {cid: {"on": spec["on"], "package": spec.get("package", "")} for cid, spec in CONSENTS.items()}}


def build(purposes, consents, skipped=()) -> Plan:
    if not isinstance(purposes, (list, tuple)) or any(p not in PURPOSES for p in purposes):
        raise PlanError("invalid_purpose")
    if not isinstance(consents, dict) or any(k not in CONSENTS or not isinstance(v, bool) for k, v in consents.items()):
        raise PlanError("invalid_consent")
    chosen = _ordered(purposes)
    asked = _ordered(c for p in chosen for c in PURPOSES[p]["consents"])
    skip = set(skipped or ())
    included = tuple(k for k in _ordered(k for p in chosen for k in PURPOSES[p]["enable"]) if k not in skip)
    updates = {key: "1" for key in included}
    packages = [pkg for p in chosen for pkg in PURPOSES[p]["packages"]]
    for cid in asked:
        answer = consents.get(cid)
        if answer is None:
            continue
        updates.update(CONSENTS[cid]["on" if answer else "off"])
        if answer and CONSENTS[cid].get("package"):
            packages.append(CONSENTS[cid]["package"])
    pending = tuple(c for c in asked if c not in consents)
    denied = tuple(CONSENTS[c]["package"] for c in CONSENTS if consents.get(c) is False and CONSENTS[c].get("package"))
    allowed = tuple(p for p in _ordered(packages) if p in WIZARD_PACKAGES)
    return Plan(chosen, asked, pending, updates, tuple(p for p in allowed if p not in denied), denied, included)
