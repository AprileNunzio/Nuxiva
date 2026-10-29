from __future__ import annotations

import fnmatch
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from features.hardware.localization import translate

from typing import Dict, Iterable, List, Optional, Tuple

log = logging.getLogger("nuxiva.hardware.identify")

SYSFS = Path(os.environ.get("NUXIVA_SYSFS", "/sys"))

PCI_IDS_PATHS = (
    "/usr/share/hwdata/pci.ids",
    "/usr/share/misc/pci.ids",
    "/usr/share/pci.ids",
    "/var/lib/pciutils/pci.ids",
)
USB_IDS_PATHS = (
    "/usr/share/hwdata/usb.ids",
    "/usr/share/misc/usb.ids",
    "/usr/share/usb.ids",
    "/var/lib/usbutils/usb.ids",
)


USB_SERIAL_VENDORS = {"0403", "10c4", "1a86", "067b", "04d8", "2341", "2a03", "1b4f", "16c0", "0483"}

PCI_INFRA_BASE = {0x05, 0x06, 0x08, 0x0C, 0x10, 0x11, 0x13, 0xFF}

ICONS = {
    "wifi": "📶",
    "network": "🌐",
    "bluetooth": "ᛒ",
    "gpu": "🎮",
    "accelerator": "🧠",
    "audio": "🔊",
    "camera": "📷",
    "input": "🖱️",
    "storage": "💾",
    "serial": "🔗",
    "printer": "🖨️",
    "cellular": "📡",
    "platform": "🧩",
    "other": "🔌",
}


@dataclass
class Identity:


    bus: str
    sys_id: str
    vendor_id: str = ""
    product_id: str = ""
    vendor_name: str = ""
    product_name: str = ""
    category: str = "other"
    modalias: str = ""
    class_code: int = -1
    kernel_modules: List[str] = field(default_factory=list)
    bound_driver: Optional[str] = None
    interface: Optional[str] = None
    all_modaliases: List[str] = field(default_factory=list)

    @property
    def icon(self) -> str:
        return ICONS.get(self.category, ICONS["other"])

    @property
    def display_name(self) -> str:
        parts = [p for p in (self.vendor_name, self.product_name) if p]
        if parts:
            return " ".join(parts)
        if self.vendor_id and self.product_id:
            return translate("hardware_device", bus=self.bus.upper(), id=f"{self.vendor_id}:{self.product_id}")
        return translate("hardware_device", bus=self.bus.upper(), id=self.sys_id)


_USB_RE = re.compile(
    r"^usb:v(?P<v>[0-9A-Fa-f]{4})p(?P<p>[0-9A-Fa-f]{4})d[0-9A-Fa-f]{4}"
    r"dc(?P<dc>[0-9A-Fa-f]{2})dsc(?P<dsc>[0-9A-Fa-f]{2})dp(?P<dp>[0-9A-Fa-f]{2})"
    r"ic(?P<ic>[0-9A-Fa-f]{2})isc(?P<isc>[0-9A-Fa-f]{2})ip(?P<ip>[0-9A-Fa-f]{2})"
)
_PCI_RE = re.compile(
    r"^pci:v(?P<v>[0-9A-Fa-f]{8})d(?P<d>[0-9A-Fa-f]{8})"
    r"sv(?P<sv>[0-9A-Fa-f]{8})sd(?P<sd>[0-9A-Fa-f]{8})"
    r"bc(?P<bc>[0-9A-Fa-f]{2})sc(?P<sc>[0-9A-Fa-f]{2})i(?P<i>[0-9A-Fa-f]{2})"
)
_ACPI_RE = re.compile(r"^acpi:(?P<ids>[A-Za-z0-9_:]+?):?$")


def parse_modalias(modalias: str) -> Dict[str, str]:

    text = (modalias or "").strip()
    m = _USB_RE.match(text)
    if m:
        out = {k: v.lower() for k, v in m.groupdict().items()}
        out["bus"] = "usb"
        out["vendor"] = out.pop("v")
        out["product"] = out.pop("p")
        return out
    m = _PCI_RE.match(text)
    if m:
        out = {k: v.lower() for k, v in m.groupdict().items()}
        out["bus"] = "pci"
        out["vendor"] = out.pop("v")[-4:]
        out["product"] = out.pop("d")[-4:]
        return out
    m = _ACPI_RE.match(text)
    if m:
        ids = [x for x in m.group("ids").split(":") if x]
        return {"bus": "acpi", "vendor": ids[0] if ids else "", "product": "", "ids": ",".join(ids)}
    return {}


def usb_class_to_category(vendor: str, ic: int, isc: int, ip: int) -> str:

    if ic == 0xE0 and isc == 0x01:
        return "bluetooth" if ip == 0x01 else "network"
    if ic == 0x01:
        return "audio"
    if ic == 0x0E:
        return "camera"
    if ic == 0x03:
        return "input"
    if ic == 0x08:
        return "storage"
    if ic == 0x07:
        return "printer"
    if ic == 0x02 and isc in (0x02, 0x0A):
        return "serial"
    if ic == 0x02 and isc in (0x06, 0x0D):
        return "network"
    if ic == 0x0A:
        return "network"
    if ic == 0xFF and vendor in USB_SERIAL_VENDORS:
        return "serial"
    return "other"


def pci_class_to_category(class_code: int) -> Optional[str]:

    base = (class_code >> 16) & 0xFF
    sub = (class_code >> 8) & 0xFF
    if base in PCI_INFRA_BASE:
        return None
    if base == 0x02:
        return "network" if sub == 0x00 else ("wifi" if sub == 0x80 else "network")
    if base == 0x03:
        return "gpu"
    if base == 0x04:
        return "audio" if sub in (0x01, 0x03) else "camera"
    if base == 0x0D:
        return "bluetooth" if sub == 0x11 else "wifi"
    if base == 0x12:
        return "accelerator"
    if base == 0x07:

        return "serial" if sub in (0x00, 0x02, 0x03) else None
    if base == 0x01:
        return None
    if base == 0x09:
        return "input"
    return "other"


class IdsDatabase:


    def __init__(self, paths: Iterable[str]) -> None:
        self._paths = tuple(paths)
        self._vendors: Dict[str, str] = {}
        self._devices: Dict[Tuple[str, str], str] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for p in self._paths:
            path = Path(p)
            if not path.is_file():
                continue
            try:
                vendor = ""
                for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if not raw or raw.startswith("#"):
                        continue
                    if raw.startswith("C "):
                        break
                    if raw.startswith("\t\t"):
                        continue
                    if raw.startswith("\t"):
                        did, _, name = raw[1:].partition("  ")
                        if vendor and len(did) == 4:
                            self._devices[(vendor, did.lower())] = name.strip()
                    else:
                        vid, _, name = raw.partition("  ")
                        if len(vid) == 4:
                            vendor = vid.lower()
                            self._vendors[vendor] = name.strip()
                        else:
                            vendor = ""
                return
            except OSError as exc:
                log.debug("ids %s non leggibile: %s", p, exc)

    def vendor(self, vid: str) -> str:
        self._load()
        return self._vendors.get(vid.lower(), "")

    def device(self, vid: str, did: str) -> str:
        self._load()
        return self._devices.get((vid.lower(), did.lower()), "")


pci_ids = IdsDatabase(PCI_IDS_PATHS)
usb_ids = IdsDatabase(USB_IDS_PATHS)


class ModulesAlias:


    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path
        self._by_bus: Dict[str, List[Tuple[str, str]]] = {}
        self._loaded = False
        self._cache: Dict[str, List[str]] = {}
        self._signature = None

    def _resolve_path(self) -> Optional[Path]:
        if self._path:
            return self._path
        try:
            release = os.uname().release
        except AttributeError:
            return None
        return Path("/lib/modules") / release / "modules.alias"

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = self._resolve_path()
        if not path or not path.is_file():
            return
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.startswith("alias "):
                    continue
                parts = line.split()
                if len(parts) != 3:
                    continue
                pattern, module = parts[1], parts[2]
                bus = pattern.split(":", 1)[0].rstrip("*")
                self._by_bus.setdefault(bus, []).append((pattern, module))
        except OSError as exc:
            log.debug("modules.alias non leggibile: %s", exc)

    def modules_for(self, modalias: str) -> List[str]:
        if not modalias or len(modalias) > 512:
            return []
        path = self._resolve_path()
        try:
            signature = (str(path), path.stat().st_mtime_ns, path.stat().st_size) if path else None
        except FileNotFoundError:
            signature = None
        if signature != self._signature:
            self._signature = signature
            self._loaded = False
            self._by_bus.clear()
            self._cache.clear()
        if modalias in self._cache:
            return list(self._cache[modalias])
        self._load()
        bus = modalias.split(":", 1)[0]
        found: List[str] = []
        for pattern, module in self._by_bus.get(bus, ()):
            if fnmatch.fnmatchcase(modalias, pattern) and module not in found:
                found.append(module)
        if len(self._cache) >= 4096:
            self._cache.clear()
        self._cache[modalias] = list(found)
        return found

    @property
    def available(self) -> bool:
        self._load()
        return bool(self._by_bus)


modules_alias = ModulesAlias()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        log.warning("sysfs read failed (%s): %s", path, exc)
        return ""


def _driver_of(path: Path) -> Optional[str]:
    link = path / "driver"
    if link.is_symlink():
        try:
            return link.resolve().name
        except OSError:
            return None
    return None


def _net_iface(path: Path) -> Optional[str]:
    net = path / "net"
    if net.is_dir():
        for child in sorted(net.iterdir()):
            return child.name
    return None


def scan_usb(sysfs: Path = SYSFS, alias: ModulesAlias = modules_alias) -> List[Identity]:
    base = sysfs / "bus" / "usb" / "devices"
    found: List[Identity] = []
    if not base.is_dir():
        return found
    for dev in sorted(base.iterdir()):
        vid = _read(dev / "idVendor").lower()
        pid = _read(dev / "idProduct").lower()
        if not vid or not pid or vid == "1d6b":
            continue
        ident = Identity(bus="usb", sys_id=dev.name, vendor_id=vid, product_id=pid)
        ident.vendor_name = _read(dev / "manufacturer") or usb_ids.vendor(vid)
        ident.product_name = _read(dev / "product") or usb_ids.device(vid, pid)
        best: Optional[str] = None
        for child in sorted(dev.iterdir()):
            if not child.name.startswith(f"{dev.name}:"):
                continue
            modalias = _read(child / "modalias")
            if not modalias:
                continue
            fields = parse_modalias(modalias)
            if not fields:
                continue
            ic, isc, ip = (int(fields[k], 16) for k in ("ic", "isc", "ip"))
            if ic == 0x09:
                continue
            ident.all_modaliases.append(modalias)
            cat = usb_class_to_category(vid, ic, isc, ip)
            if best is None or (best == "other" and cat != "other") or cat in ("wifi", "bluetooth", "serial"):
                best = cat
                ident.modalias = modalias
                ident.class_code = (ic << 16) | (isc << 8) | ip
            for mod in alias.modules_for(modalias):
                if mod not in ident.kernel_modules:
                    ident.kernel_modules.append(mod)
            ident.bound_driver = ident.bound_driver or _driver_of(child)
            ident.interface = ident.interface or _net_iface(child)
        if not ident.all_modaliases:
            continue
        ident.category = best or "other"
        if ident.interface and ident.category == "other":
            ident.category = "wifi" if ident.interface.startswith(("wl", "wlan")) else "network"
        found.append(ident)
    return found


def scan_pci(sysfs: Path = SYSFS, alias: ModulesAlias = modules_alias) -> List[Identity]:
    base = sysfs / "bus" / "pci" / "devices"
    found: List[Identity] = []
    if not base.is_dir():
        return found
    for dev in sorted(base.iterdir()):
        try:
            class_code = int(_read(dev / "class") or "0", 16)
        except ValueError:
            continue
        category = pci_class_to_category(class_code)
        if category is None:
            continue
        vid = _read(dev / "vendor").lower().replace("0x", "").zfill(4)
        did = _read(dev / "device").lower().replace("0x", "").zfill(4)
        modalias = _read(dev / "modalias")
        ident = Identity(
            bus="pci",
            sys_id=dev.name,
            vendor_id=vid,
            product_id=did,
            vendor_name=pci_ids.vendor(vid),
            product_name=pci_ids.device(vid, did),
            category=category,
            modalias=modalias,
            class_code=class_code,
            bound_driver=_driver_of(dev),
            interface=_net_iface(dev),
            all_modaliases=[modalias] if modalias else [],
        )
        ident.kernel_modules = alias.modules_for(modalias)
        found.append(ident)
    return found


def scan_acpi(sysfs: Path = SYSFS, alias: ModulesAlias = modules_alias) -> List[Identity]:


    base = sysfs / "bus" / "acpi" / "devices"
    found: List[Identity] = []
    if not base.is_dir():
        return found
    for dev in sorted(base.iterdir()):
        modalias = _read(dev / "modalias")
        if not modalias.startswith("acpi:"):
            continue
        status = _read(dev / "status")
        if status and (not status.isdecimal() or not int(status) & 1):
            continue
        modules = alias.modules_for(modalias)
        driver = _driver_of(dev) or _driver_of(dev / "physical_node")
        if not modules and not driver:
            continue
        fields = parse_modalias(modalias)
        found.append(
            Identity(
                bus="acpi",
                sys_id=dev.name,
                vendor_id=fields.get("vendor", ""),
                product_name=_read(dev / "path") or dev.name,
                category="platform",
                bound_driver=driver,
                modalias=modalias,
                all_modaliases=[modalias],
                kernel_modules=modules,
            )
        )
    return found


def scan_all(sysfs: Path = SYSFS, alias: ModulesAlias = modules_alias) -> List[Identity]:

    return scan_usb(sysfs, alias) + scan_pci(sysfs, alias) + scan_acpi(sysfs, alias) + scan_auxiliary(sysfs, alias)


def scan_auxiliary(sysfs: Path = SYSFS, alias: ModulesAlias = modules_alias) -> List[Identity]:
    found = []
    for bus in ("i2c", "spi", "thunderbolt"):
        base = sysfs / "bus" / bus / "devices"
        if not base.is_dir():
            continue
        for device in sorted(base.iterdir()):
            modalias = _read(device / "modalias")
            if not modalias:
                continue
            driver, modules = _driver_of(device), alias.modules_for(modalias)
            found.append(Identity(bus=bus, sys_id=device.name, category="platform",
                                  product_name=_read(device / "name"), modalias=modalias,
                                  bound_driver=driver, kernel_modules=modules, all_modaliases=[modalias]))
    return found
