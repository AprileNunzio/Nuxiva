from __future__ import annotations

import asyncio
import glob
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from features.hardware.expert import agent as hardware_agent
from features.hardware.model import HardwareDevice
from state import store

log = logging.getLogger("nuxiva.hardware")
SCAN_INTERVAL = 4.0


class HardwareService:
    def __init__(self) -> None:
        self._devices: Dict[str, HardwareDevice] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._provisioning_tasks: Dict[str, asyncio.Task] = {}

    @property
    def devices(self) -> List[HardwareDevice]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Optional[HardwareDevice]:
        return self._devices.get(device_id)

    def _read_sysfs(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def _scan_linux_usb(self) -> List[HardwareDevice]:
        devices: List[HardwareDevice] = []
        base = Path("/sys/bus/usb/devices")
        if not base.exists():
            return devices

        for dev_path in base.iterdir():
            vendor_file = dev_path / "idVendor"
            product_file = dev_path / "idProduct"
            if not vendor_file.is_file() or not product_file.is_file():
                continue

            vid = self._read_sysfs(vendor_file).lower()
            pid = self._read_sysfs(product_file).lower()
            if not vid or not pid or vid == "1d6b":  # skip root hubs
                continue

            mfg = self._read_sysfs(dev_path / "manufacturer")
            prod = self._read_sysfs(dev_path / "product")

            driver = None
            iface_name = None
            category = "other"
            icon = "🔌"

            # Check interface drivers and network devices
            for child in dev_path.iterdir():
                if child.name.startswith(f"{dev_path.name}:"):
                    drv_link = child / "driver"
                    if drv_link.is_symlink():
                        driver = drv_link.resolve().name
                    net_dir = child / "net"
                    if net_dir.is_dir():
                        for net_dev in net_dir.iterdir():
                            iface_name = net_dev.name
                            break

            # Categorization
            if vid == "148f" and pid == "2573":
                name = "TP-Link TL-WN321G Wireless Adapter (Ralink RT2573)"
                vendor = "TP-Link / Ralink"
                category = "wifi"
                icon = "📶"
            elif category == "other":
                prod_lower = f"{(mfg or '').lower()} {(prod or '').lower()}"
                if any(w in prod_lower for w in ("wireless", "802.11", "wlan", "wifi")) or (driver and "wifi" in driver) or (iface_name and iface_name.startswith(("wl", "wlan"))):
                    category = "wifi"
                    icon = "📶"
                elif any(w in prod_lower for w in ("bluetooth", "bt")) or (driver and "bt" in driver):
                    category = "bluetooth"
                    icon = "ᛒ"
                elif any(w in prod_lower for w in ("camera", "webcam", "video")):
                    category = "camera"
                    icon = "📷"
                elif any(w in prod_lower for w in ("audio", "sound", "headset", "microphone")):
                    category = "audio"
                    icon = "🔊"
                elif any(w in prod_lower for w in ("keyboard", "mouse", "optical")):
                    category = "input"
                    icon = "🖱️"
                elif any(w in prod_lower for w in ("storage", "disk", "flash", "crw")):
                    category = "storage"
                    icon = "💾"

                name = f"{mfg} {prod}".strip() or f"Dispositivo USB {vid}:{pid}"
                vendor = mfg or "USB Vendor"

            dev_id = f"usb:{vid}:{pid}:{dev_path.name}"
            dev = HardwareDevice(
                id=dev_id,
                name=name,
                vendor=vendor,
                vendor_id=vid,
                product_id=pid,
                category=category,
                bus="usb",
                driver=driver,
                interface=iface_name,
                icon=icon,
            )
            devices.append(dev)

        return devices

    def _scan_linux_interfaces(self, existing_usb: List[HardwareDevice]) -> List[HardwareDevice]:
        devices: List[HardwareDevice] = []
        known_ifaces = {d.interface for d in existing_usb if d.interface}
        sys_net = Path("/sys/class/net")
        if not sys_net.exists():
            return devices

        for if_path in sys_net.iterdir():
            name = if_path.name
            if name == "lo" or name in known_ifaces or name.startswith(("docker", "veth", "br-", "nuxiva-sbx")):
                continue

            is_wifi = (
                (if_path / "wireless").exists()
                or (if_path / "phy80211").exists()
                or name.startswith(("wl", "wlan", "wlp", "wlx"))
            )
            category = "wifi" if is_wifi else "network"
            icon = "📶" if is_wifi else "🌐"
            dev_id = f"net:{name}"

            dev = HardwareDevice(
                id=dev_id,
                name=f"Interfaccia di rete {name}" + (" (Wi-Fi)" if is_wifi else " (Ethernet)"),
                vendor="Linux Network Device",
                vendor_id="",
                product_id="",
                category=category,
                bus="pci" if not name.startswith("wlx") else "usb",
                interface=name,
                icon=icon,
                status="ready",
                status_label="Attiva",
            )
            devices.append(dev)

        return devices

    def _scan_linux_bluetooth(self, existing_usb: List[HardwareDevice]) -> List[HardwareDevice]:
        devices: List[HardwareDevice] = []
        has_bt_usb = any(d.category == "bluetooth" for d in existing_usb)
        sys_bt = Path("/sys/class/bluetooth")
        if sys_bt.exists():
            for hci in sys_bt.glob("hci*"):
                if not has_bt_usb:
                    dev_id = f"bt:{hci.name}"
                    devices.append(
                        HardwareDevice(
                            id=dev_id,
                            name=f"Controller Bluetooth ({hci.name})",
                            vendor="Bluetooth Adapter",
                            vendor_id="",
                            product_id="",
                            category="bluetooth",
                            bus="usb",
                            icon="ᛒ",
                            status="ready",
                            status_label="Pronto",
                        )
                    )
        return devices

    async def scan(self) -> List[HardwareDevice]:
        if os.name != "nt":
            usb_devs = self._scan_linux_usb()
            net_devs = self._scan_linux_interfaces(usb_devs)
            bt_devs = self._scan_linux_bluetooth(usb_devs)
            all_devs = usb_devs + net_devs + bt_devs
        else:
            # Safe basic fallback on Windows
            all_devs = []
            for p in glob.glob("/sys/class/bluetooth/hci*"):
                all_devs.append(HardwareDevice("bt:local", "Bluetooth Adapter", "Standard", "", "", "bluetooth", icon="ᛒ"))

        for dev in all_devs:
            status, pkgs, missing_fw = hardware_agent.diagnose(dev)
            dev.status = status
            dev.required_packages = pkgs
            dev.missing_firmware = missing_fw
            if status == "ready":
                dev.status_label = "Pronto all'uso"
            elif status == "needs_driver":
                dev.status_label = f"Driver mancante ({missing_fw or 'pacchetti'})"

        return all_devs

    async def refresh(self) -> List[HardwareDevice]:
        async with self._lock:
            current_list = await self.scan()
            current_map = {d.id: d for d in current_list}

            # Check new devices
            added_ids = set(current_map.keys()) - set(self._devices.keys())
            removed_ids = set(self._devices.keys()) - set(current_map.keys())

            from features.desktop.desk import desk
            from nuxiva_bus import nuxiva_bus

            for dev_id in added_ids:
                dev = current_map[dev_id]
                store.event("INFO", f"Dispositivo connesso: {dev.name}", "hardware")
                desk.show(
                    "notice",
                    {"icon": dev.icon, "title": "Dispositivo connesso", "text": dev.name},
                    key=f"hw:{dev.id}",
                    ttl=30,
                )
                nuxiva_bus.publish(
                    "ui.notification.notice",
                    {"labelKey": "os_device_connected", "device": dev.to_dict()},
                    origin="hardware",
                )

                if dev.status == "needs_driver" and dev_id not in self._provisioning_tasks:
                    log.info("Rilevato dispositivo con driver mancante: %s, avvio agente esperto", dev.name)
                    task = asyncio.create_task(hardware_agent.provision(dev))
                    self._provisioning_tasks[dev_id] = task

            for dev_id in removed_ids:
                old_dev = self._devices[dev_id]
                store.event("INFO", f"Dispositivo scollegato: {old_dev.name}", "hardware")
                desk.show(
                    "notice",
                    {"icon": "🔌", "title": "Dispositivo scollegato", "text": old_dev.name},
                    key=f"hw:{dev_id}",
                    ttl=15,
                )
                nuxiva_bus.publish(
                    "ui.notification.notice",
                    {"labelKey": "os_device_disconnected", "device": old_dev.to_dict()},
                    origin="hardware",
                )
                if dev_id in self._provisioning_tasks:
                    self._provisioning_tasks[dev_id].cancel()
                    self._provisioning_tasks.pop(dev_id, None)

            if added_ids or removed_ids:
                store.touch()

            self._devices = current_map
            return list(self._devices.values())

    async def run(self) -> None:
        self._running = True
        log.info("Servizio monitoraggio hardware e agente driver avviato")
        while self._running:
            try:
                await self.refresh()
            except Exception as exc:
                log.warning("Ciclo monitoraggio hardware non riuscito: %s", exc)
            await asyncio.sleep(SCAN_INTERVAL)


hardware_service = HardwareService()
