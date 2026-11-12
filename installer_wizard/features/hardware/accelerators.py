from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from features.hardware.catalog import PKG_KEY, catalog, distro_packages
from features.hardware.identify import Identity

log = logging.getLogger("nuxiva.hardware.accel")


FALLBACK_DRIVERS = {"nouveau", "vesafb", "simpledrm", "efifb", "vga16fb", "simplefb", "fbdev"}


@dataclass
class GpuPlan:
    vendor_id: str
    vendor_name: str = ""
    status: str = "ready"
    reason: str = ""
    packages: List[str] = field(default_factory=list)
    repos: List[str] = field(default_factory=list)
    extra_repos: List[str] = field(default_factory=list)
    verify: List[str] = field(default_factory=list)
    capability: str = ""
    reboot: bool = False
    needs_approval: bool = False
    selection_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "status": self.status,
            "reason": self.reason,
            "packages": self.packages,
            "repos": self.repos,
            "reboot": self.reboot,
            "needs_approval": self.needs_approval,
            "selection_required": self.selection_required,
            "capability": self.capability,
        }


def has_graphical_session() -> bool:

    try:
        out = subprocess.run(
            ["systemctl", "is-active", "display-manager"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        if out == "active":
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return any(Path("/tmp/.X11-unix").glob("X*")) if Path("/tmp/.X11-unix").is_dir() else False


def plan_gpu(identity: Identity, pkg_manager: str, graphical: Optional[bool] = None, distro_family: str = "") -> Optional[GpuPlan]:

    vendor = catalog.gpu_vendor(identity.vendor_id)
    if vendor is None:
        return None
    plan = GpuPlan(
        vendor_id=identity.vendor_id,
        vendor_name=vendor.get("name", ""),
        repos=list(vendor.get("repos", [])),
        verify=list(vendor.get("verify", [])),
        capability=vendor.get("capability", ""),
        reboot=bool(vendor.get("reboot", False)),
    )
    plan.packages = distro_packages(list(vendor.get("packages", {}).get(PKG_KEY.get(pkg_manager, ""), [])), distro_family)
    if distro_family == "ubuntu" and identity.vendor_id == "10de" and identity.bound_driver != "nvidia":
        plan.packages = ["ubuntu-drivers-common", "linux-firmware"]
        plan.selection_required = True
    plan.extra_repos = list(vendor.get("extra_repos", {}).get(PKG_KEY.get(pkg_manager, ""), []))
    bound = identity.bound_driver or ""
    driver_ok = set(vendor.get("driver_ok", []))
    proprietary = bool(vendor.get("needs_proprietary", False))

    if bound in driver_ok:
        plan.status = "ready"
        plan.reason = f"Driver {bound} attivo"
        return plan
    if not plan.packages:
        plan.status = "unsupported"
        plan.reason = "Nessun pacchetto automatico per questa distribuzione"
        return plan

    plan.status = "needs_driver"
    if proprietary:
        plan.reason = (
            f"Driver proprietario {plan.vendor_name} non attivo"
            + (f" (in uso: {bound})" if bound else " (nessun driver)")
        )
        if graphical is None:
            graphical = has_graphical_session()
        if graphical and bound in FALLBACK_DRIVERS:
            plan.status = "awaiting_approval"
            plan.needs_approval = True
            plan.reason += ": sessione grafica attiva, serve conferma dell'amministratore"
    else:
        plan.reason = f"Driver {plan.vendor_name} da completare" + (f" (in uso: {bound})" if bound else "")
    return plan
