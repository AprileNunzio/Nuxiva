import logging
import re

from features.hardware import identify


log = logging.getLogger("nuxiva.hardware.binding")


def reprobe(device):
    if device.bus not in ("usb", "pci", "acpi", "i2c", "spi") or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", device.sys_id):
        return False
    bus = identify.SYSFS / "bus" / device.bus
    node = bus / "devices" / device.sys_id
    probe = bus / "drivers_probe"
    if not node.exists() or not probe.exists():
        return False
    targets = [node]
    if device.bus == "usb":
        targets = [child for child in node.iterdir() if child.name.startswith(device.sys_id + ":")]
    attempted = False
    try:
        for target in targets:
            if not (target / "driver").exists():
                probe.write_text(target.name, encoding="ascii")
                attempted = True
        return attempted
    except OSError as exc:
        log.error("Device reprobe failed (%s): %s", device.id, exc)
        return False
