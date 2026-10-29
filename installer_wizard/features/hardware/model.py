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
    status_label: str = "Pronto all'uso"
    missing_firmware: Optional[str] = None
    required_packages: List[str] = field(default_factory=list)
    icon: str = "🔌"
    connected_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

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
            "status_label": self.status_label,
            "missing_firmware": self.missing_firmware,
            "required_packages": list(self.required_packages),
            "icon": self.icon,
            "connected_at": self.connected_at,
            "details": self.details,
        }
