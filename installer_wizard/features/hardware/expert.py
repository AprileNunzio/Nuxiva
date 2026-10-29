from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import re
import shutil
from typing import List, Optional, Tuple

from features.hardware.model import HardwareDevice
from state import store

log = logging.getLogger("nuxiva.hardware.expert")

# Well-known hardware driver & package signatures
KNOWN_DRIVERS = {
    ("148f", "2573"): {
        "name": "TP-Link TL-WN321G (Ralink RT2573 Wireless Adapter)",
        "category": "wifi",
        "driver": "rt73usb",
        "firmware": "rt73.bin",
        "deb_packages": ["firmware-misc-nonfree", "firmware-mediatek", "network-manager", "wpasupplicant", "wireless-tools", "iw"],
        "rpm_packages": ["linux-firmware", "NetworkManager-wifi", "wpa_supplicant", "wireless-tools", "iw"],
    },
    ("148f", "3070"): {
        "name": "Ralink RT3070 802.11n Wireless Adapter",
        "category": "wifi",
        "driver": "rt2800usb",
        "firmware": "rt2870.bin",
        "deb_packages": ["firmware-misc-nonfree", "firmware-mediatek", "network-manager", "wpasupplicant", "wireless-tools", "iw"],
        "rpm_packages": ["linux-firmware", "NetworkManager-wifi", "wpa_supplicant"],
    },
    ("148f", "5370"): {
        "name": "Ralink RT5370 802.11n Wireless Adapter",
        "category": "wifi",
        "driver": "rt2800usb",
        "firmware": "rt2870.bin",
        "deb_packages": ["firmware-misc-nonfree", "firmware-mediatek", "network-manager", "wpasupplicant", "wireless-tools", "iw"],
        "rpm_packages": ["linux-firmware", "NetworkManager-wifi", "wpa_supplicant"],
    },
    ("0cf3", "9271"): {
        "name": "Atheros AR9271 802.11n Wireless Adapter",
        "category": "wifi",
        "driver": "ath9k_htc",
        "firmware": "ath9k_htc/htc_9271-1.4.0.fw",
        "deb_packages": ["firmware-ath9k-htc", "network-manager", "wpasupplicant", "wireless-tools", "iw"],
        "rpm_packages": ["linux-firmware", "NetworkManager-wifi", "wpa_supplicant"],
    },
    ("0a12", "0001"): {
        "name": "Cambridge Silicon Radio (CSR) Bluetooth Dongle",
        "category": "bluetooth",
        "driver": "btusb",
        "firmware": None,
        "deb_packages": ["bluez", "bluez-tools", "pulseaudio-module-bluetooth"],
        "rpm_packages": ["bluez", "pulseaudio-module-bluetooth"],
    },
}

FIRMWARE_PACKAGES_DEB = {
    "rt73.bin": ["firmware-misc-nonfree", "firmware-mediatek"],
    "rt2870.bin": ["firmware-misc-nonfree", "firmware-mediatek"],
    "rt3070.bin": ["firmware-misc-nonfree", "firmware-mediatek"],
    "rt3071.bin": ["firmware-misc-nonfree", "firmware-mediatek"],
}


class HardwareAgent:
    def __init__(self) -> None:
        self._pkg_manager: Optional[str] = None
        self._lock = asyncio.Lock()

    def detect_pkg_manager(self) -> str:
        if self._pkg_manager:
            return self._pkg_manager
        if shutil.which("apt-get"):
            self._pkg_manager = "apt"
        elif shutil.which("dnf"):
            self._pkg_manager = "dnf"
        elif shutil.which("yum"):
            self._pkg_manager = "yum"
        elif shutil.which("zypper"):
            self._pkg_manager = "zypper"
        elif shutil.which("pacman"):
            self._pkg_manager = "pacman"
        else:
            self._pkg_manager = "generic"
        return self._pkg_manager

    async def _run_cmd(self, cmd: List[str], timeout: float = 180) -> Tuple[int, str]:
        try:
            env = dict(os.environ)
            env["DEBIAN_FRONTEND"] = "noninteractive"
            env["APT_LISTCHANGES_FRONTEND"] = "none"
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, out.decode("utf-8", "replace")
        except Exception as exc:
            log.warning("Comando %s non riuscito: %s", cmd, exc)
            return 1, str(exc)

    async def _scan_dmesg_missing_firmware(self) -> List[str]:
        missing: List[str] = []
        code, out = await self._run_cmd(["dmesg"], timeout=10)
        if code == 0:
            for line in out.splitlines()[-200:]:
                m = re.search(r"(?:failed to load|Direct firmware load for)\s+([a-zA-Z0-9_\-\./]+)", line)
                if m:
                    fw_name = Path(m.group(1)).name
                    if fw_name not in missing:
                        missing.append(fw_name)
        return missing

    def diagnose(self, device: HardwareDevice) -> Tuple[str, List[str], Optional[str]]:
        pkg_mgr = self.detect_pkg_manager()
        is_rpm = pkg_mgr in ("yum", "dnf")

        key = (device.vendor_id.lower(), device.product_id.lower())
        sig = KNOWN_DRIVERS.get(key)
        pkgs: List[str] = []
        missing_fw: Optional[str] = None

        if sig:
            pkgs = list(sig["rpm_packages"] if is_rpm else sig["deb_packages"])
            missing_fw = sig.get("firmware")
        elif device.category == "wifi":
            if is_rpm:
                pkgs = ["linux-firmware", "NetworkManager-wifi", "wpa_supplicant", "wireless-tools", "iw"]
            else:
                pkgs = ["firmware-misc-nonfree", "network-manager", "wpasupplicant", "wireless-tools", "iw"]
        elif device.category == "bluetooth":
            pkgs = ["bluez", "pulseaudio-module-bluetooth"] if is_rpm else ["bluez", "bluez-tools", "pulseaudio-module-bluetooth"]

        needs_driver = False
        if missing_fw:
            fw_candidates = [Path("/lib/firmware") / missing_fw, Path("/usr/lib/firmware") / missing_fw]
            if not any(p.exists() for p in fw_candidates):
                needs_driver = True

        if device.category == "wifi" and not shutil.which("nmcli") and not shutil.which("iw"):
            needs_driver = True

        if device.category == "bluetooth" and not shutil.which("bluetoothctl"):
            needs_driver = True

        status = "needs_driver" if needs_driver else "ready"
        return status, pkgs, missing_fw

    async def update_packages(self) -> Tuple[int, str]:
        pkg_mgr = self.detect_pkg_manager()
        log.info("Agente Hardware: Aggiornamento sorgenti pacchetti tramite %s", pkg_mgr)
        if pkg_mgr == "apt":
            return await self._run_cmd(["apt-get", "update"], timeout=180)
        elif pkg_mgr in ("yum", "dnf"):
            return await self._run_cmd([pkg_mgr, "check-update"], timeout=180)
        elif pkg_mgr == "zypper":
            return await self._run_cmd(["zypper", "refresh"], timeout=180)
        elif pkg_mgr == "pacman":
            return await self._run_cmd(["pacman", "-Sy"], timeout=180)
        return 0, "No supported package manager"

    async def install_packages(self, packages: List[str]) -> Tuple[int, str]:
        if not packages:
            return 0, "Nessun pacchetto richiesto"
        pkg_mgr = self.detect_pkg_manager()
        log.info("Agente Hardware: Installazione driver/pacchetti %s tramite %s", packages, pkg_mgr)
        if pkg_mgr == "apt":
            cmd = ["apt-get", "install", "-y", "--no-install-recommends", *packages]
        elif pkg_mgr in ("yum", "dnf"):
            cmd = [pkg_mgr, "install", "-y", *packages]
        elif pkg_mgr == "zypper":
            cmd = ["zypper", "install", "-y", *packages]
        elif pkg_mgr == "pacman":
            cmd = ["pacman", "-S", "--noconfirm", *packages]
        else:
            return 1, "Package manager non supportato per installazione automatica"
        return await self._run_cmd(cmd, timeout=600)

    async def activate_device(self, device: HardwareDevice) -> bool:
        try:
            if device.category == "wifi":
                if device.driver:
                    await self._run_cmd(["modprobe", "-r", device.driver], timeout=15)
                    await asyncio.sleep(1)
                    await self._run_cmd(["modprobe", device.driver], timeout=15)
                    await asyncio.sleep(1)

                if shutil.which("systemctl"):
                    await self._run_cmd(["systemctl", "enable", "--now", "NetworkManager"], timeout=20)

                await self._run_cmd(["rfkill", "unblock", "wifi"], timeout=10)
                await self._run_cmd(["rfkill", "unblock", "all"], timeout=10)

                if device.interface:
                    await self._run_cmd(["ip", "link", "set", device.interface, "up"], timeout=10)

                if shutil.which("nmcli"):
                    await self._run_cmd(["nmcli", "radio", "wifi", "on"], timeout=10)

            elif device.category == "bluetooth":
                await self._run_cmd(["rfkill", "unblock", "bluetooth"], timeout=10)
                if shutil.which("systemctl"):
                    await self._run_cmd(["systemctl", "enable", "--now", "bluetooth"], timeout=20)
                if shutil.which("bluetoothctl"):
                    await self._run_cmd(["bluetoothctl", "power", "on"], timeout=15)

            return True
        except Exception as exc:
            log.warning("Attivazione dispositivo %s non riuscita: %s", device.name, exc)
            return False

    async def provision(self, device: HardwareDevice) -> bool:
        async with self._lock:
            status, pkgs, missing_fw = self.diagnose(device)
            device.required_packages = pkgs
            device.missing_firmware = missing_fw

            if status == "ready":
                device.status = "ready"
                device.status_label = "Pronto all'uso"
                return True

            device.status = "configuring"
            device.status_label = "Installazione driver in corso..."
            store.event("INFO", f"Agente Hardware: Avvio installazione driver per {device.name}", "hardware")

            from features.desktop.desk import desk
            from nuxiva_bus import nuxiva_bus

            desk.show(
                "notice",
                {"icon": "⚙️", "title": "Agente Hardware", "text": f"Installazione driver per {device.name}..."},
                key=f"hw:{device.id}",
                ttl=60,
            )
            nuxiva_bus.publish(
                "ui.notification.notice",
                {"labelKey": "os_device_configuring", "device": device.to_dict()},
                origin="hardware",
            )

            # 1. Update packages
            await self.update_packages()

            # 2. Check dynamic missing firmware from dmesg if any
            dmesg_fw = await self._scan_dmesg_missing_firmware()
            for fw in dmesg_fw:
                extra = FIRMWARE_PACKAGES_DEB.get(fw, [])
                for p in extra:
                    if p not in pkgs:
                        pkgs.append(p)

            # 3. Install packages
            code, out = await self.install_packages(pkgs)
            if code != 0:
                device.status = "error"
                device.status_label = "Errore installazione pacchetti"
                store.event("WARN", f"Agente Hardware: Errore installazione driver per {device.name}: {out[-200:]}", "hardware")
                return False

            # 4. Activate hardware
            await self.activate_device(device)

            # 5. Final check
            device.status = "ready"
            device.status_label = "Pronto all'uso"
            store.event("INFO", f"Agente Hardware: {device.name} configurato e pronto all'uso", "hardware")
            store.touch()

            desk.show(
                "notice",
                {"icon": "✅", "title": "Hardware Pronto", "text": f"{device.name} è pronto per l'uso"},
                key=f"hw:{device.id}",
                ttl=15,
            )
            nuxiva_bus.publish(
                "ui.notification.notice",
                {"labelKey": "os_device_ready", "device": device.to_dict()},
                origin="hardware",
            )
            return True


agent = HardwareAgent()
