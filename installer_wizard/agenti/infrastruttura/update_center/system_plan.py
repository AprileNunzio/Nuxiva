from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Tuple

try:
    import nuxiva_native as _native
except ImportError:
    _native = None

_REQUIRED = ("update_system_parse", "update_system_plan", "update_system_auto_config", "update_valid_package")
RUST = _native is not None and all(hasattr(_native, name) for name in _REQUIRED)
ENGINE = "rust" if RUST else "python"

MAX_PACKAGES = 4000
MAX_NAME = 100
MAX_INPUT = 16 * 1024 * 1024
REBOOT_PREFIXES = ("linux-image-", "libc6", "systemd", "udev", "dbus", "grub-")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+\-:]*$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def valid_package(name: str) -> bool:
    if RUST:
        return bool(_native.update_valid_package(name))
    return 0 < len(name) <= MAX_NAME and bool(_NAME.match(name))


def _bounded(raw: str) -> str:
    if len(raw) > MAX_INPUT:
        raise ValueError("input too large")
    return raw


def _token(raw: str) -> str:
    return _CONTROL.sub("", raw.strip("[](),"))[:MAX_NAME]


def _parse_inst(rest: str) -> Tuple[Dict[str, Any], bool] | None:
    parts = rest.split()
    if len(parts) < 2 or not valid_package(parts[0]):
        return None
    name = parts[0]
    if parts[1].startswith("["):
        if len(parts) < 3:
            return None
        origin_from, target, tail = _token(parts[1]), parts[2], parts[3:]
    else:
        origin_from, target, tail = "", parts[1], parts[2:]
    origin: List[str] = []
    for item in tail:
        if item.startswith("["):
            break
        origin.append(item)
    change = {"name": name, "from": origin_from, "to": _token(target), "security": "security" in " ".join(origin).lower()}
    return change, origin_from == ""


def _py_parse(raw: str) -> Dict[str, Any]:
    sim: Dict[str, Any] = {"upgrades": [], "installs": [], "removals": [], "kept_back": []}
    in_kept = False
    for line in raw.splitlines():
        if line.startswith("The following packages have been kept back"):
            in_kept = True
            continue
        if in_kept:
            if line.startswith(" "):
                for name in line.split():
                    if valid_package(name) and len(sim["kept_back"]) < MAX_PACKAGES:
                        sim["kept_back"].append(name)
                continue
            in_kept = False
        if line.startswith("Inst "):
            if len(sim["upgrades"]) + len(sim["installs"]) >= MAX_PACKAGES:
                continue
            parsed = _parse_inst(line[5:])
            if parsed is None:
                continue
            change, is_new = parsed
            if is_new:
                sim["installs"].append(change["name"])
            else:
                sim["upgrades"].append(change)
        elif line.startswith("Remv "):
            fields = line[5:].split()
            if fields and valid_package(fields[0]) and len(sim["removals"]) < MAX_PACKAGES:
                sim["removals"].append(fields[0])
    return sim


def parse(raw: str) -> Dict[str, Any]:
    if RUST:
        return json.loads(_native.update_system_parse(_bounded(raw)))
    return _py_parse(_bounded(raw))


def _reboot_package(name: str) -> bool:
    return any(name == p.rstrip("-") or name.startswith(p) for p in REBOOT_PREFIXES)


def _plan_id(sim: Dict[str, Any], target: str) -> str:
    lines = [f"u|{c['name']}|{c['to']}" for c in sim["upgrades"]]
    lines += [f"i|{n}" for n in sim["installs"]]
    lines += [f"r|{n}" for n in sim["removals"]]
    lines.sort()
    lines.append(f"n|{target}")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def _py_plan(raw: str, nuxiva: bool, target: str) -> Dict[str, Any]:
    sim = _py_parse(raw)
    packages = len(sim["upgrades"]) + len(sim["installs"])
    removals = len(sim["removals"])
    installs = len(sim["installs"])
    reboot = any(_reboot_package(c["name"]) for c in sim["upgrades"]) or any(_reboot_package(n) for n in sim["installs"])
    risk = "high" if removals else "medium" if reboot or installs else "low"
    steps: List[Dict[str, Any]] = []
    if packages or removals:
        steps.append({"id": "debian", "count": packages + removals})
    if nuxiva:
        steps.append({"id": "nuxiva", "count": 1})
    return {
        "id": _plan_id(sim, target if nuxiva else ""),
        "steps": steps,
        "packages": packages,
        "security": sum(1 for c in sim["upgrades"] if c["security"]),
        "installs": installs,
        "removals": removals,
        "kept_back": len(sim["kept_back"]),
        "nuxiva": nuxiva,
        "reboot_likely": reboot,
        "risk": risk,
        "needs_confirmation": removals > 0,
    }


def plan(raw: str, nuxiva_available: bool, nuxiva_target: str = "") -> Dict[str, Any]:
    if RUST:
        return json.loads(_native.update_system_plan(_bounded(raw), nuxiva_available, nuxiva_target))
    return _py_plan(_bounded(raw), nuxiva_available, nuxiva_target)


def _py_auto_config(enabled: bool) -> List[Dict[str, str]]:
    flag = "1" if enabled else "0"
    return [
        {
            "name": "20nuxiva-auto-upgrades",
            "content": f'APT::Periodic::Update-Package-Lists "{flag}";\nAPT::Periodic::Unattended-Upgrade "{flag}";\n',
        },
        {
            "name": "52nuxiva-unattended-upgrades",
            "content": (
                "#clear Unattended-Upgrade::Origins-Pattern;\n"
                "Unattended-Upgrade::Origins-Pattern {\n"
                '    "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";\n'
                '    "origin=Debian,codename=${distro_codename},label=Debian-Security";\n'
                "};\n"
                'Unattended-Upgrade::AutoFixInterruptedDpkg "true";\n'
                'Unattended-Upgrade::MinimalSteps "true";\n'
                'Unattended-Upgrade::Remove-Unused-Kernel-Packages "false";\n'
                'Unattended-Upgrade::Remove-Unused-Dependencies "false";\n'
                'Unattended-Upgrade::Automatic-Reboot "false";\n'
            ),
        },
    ]


def auto_config(enabled: bool) -> List[Dict[str, str]]:
    if RUST:
        return json.loads(_native.update_system_auto_config(enabled))
    return _py_auto_config(enabled)
