from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional


@dataclass
class HardwareDevice:
    id: str
    name: str
    vendor: str
    vendor_id: str
    product_id: str
    category: str
    bus: str = "usb"
    driver: Optional[str] = None
    interface: Optional[str] = None
    status: str = "ready"
    status_label: str = "hardware_ready"
    missing_firmware: Optional[str] = None
    required_packages: List[str] = field(default_factory=list)
    icon: str = "🔌"
    connected_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    sys_id: str = ""
    modalias: str = ""
    kernel_modules: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def add_step(self, tier: str, action: str, ok: bool, note: str = "") -> None:

        self.steps.append({"tier": tier, "action": action, "ok": ok, "note": note[:300], "at": time.time()})
        del self.steps[:-40]

    def brief(self) -> Dict[str, Any]:

        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "bus": self.bus,
            "icon": self.icon,
            "status": self.status,
            "status_label": "hardware_" + self.status,
            "status_label_key": "hardware_" + self.status,
            "interface": self.interface,
            "capabilities": list(self.capabilities),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "category": self.category,
            "bus": self.bus,
            "driver": self.driver,
            "interface": self.interface,
            "status": self.status,
            "status_label": "hardware_" + self.status,
            "status_label_key": "hardware_" + self.status,
            "missing_firmware": self.missing_firmware,
            "required_packages": list(self.required_packages),
            "icon": self.icon,
            "connected_at": self.connected_at,
            "details": self.details,
            "sys_id": self.sys_id,
            "modalias": self.modalias,
            "kernel_modules": list(self.kernel_modules),
            "capabilities": list(self.capabilities),
            "steps": list(self.steps),
        }
