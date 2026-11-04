import os
import tempfile
from pathlib import Path
from features.hardware.model import HardwareDevice
from features.hardware.repos import OsInfo


DEBIAN13 = OsInfo("debian", [], "13")


DEBIAN11 = OsInfo("debian", [], "11")


UBUNTU = OsInfo("ubuntu", ["debian"], "24.04")


SOURCES = """\
#deb cdrom:[Debian GNU/Linux 13]/ trixie contrib main non-free-firmware

deb http://deb.debian.org/debian/ trixie main non-free-firmware
deb-src http://deb.debian.org/debian/ trixie main non-free-firmware

deb http://security.debian.org/debian-security trixie-security main non-free-firmware
deb [arch=amd64] https://download.docker.com/linux/debian trixie stable
"""


DEB822 = """\
Types: deb
URIs: http://deb.debian.org/debian
Suites: trixie
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
"""


ALIAS = """\
# comment
alias usb:v148Fp2573d*dc*dsc*dp*ic*isc*ip*in* rt73usb
alias usb:v0BDAp8153d*dc*dsc*dp*ic*isc*ip*in* r8152
alias pci:v000010ECd00008168sv*sd*bc*sc*i* r8169
alias pci:v00008086d00001912sv*sd*bc03sc*i* i915
alias acpi*:INT3400:* int3400_thermal
alias acpi:INT3400: int3400_thermal
alias usb:v0BDAp8812d*dc*dsc*dp*ic*isc*ip*in* rtl8812au_fake
"""


PCI_IDS = """\
# pci ids
8086  Intel Corporation
\t1912  HD Graphics 530
\t\t1028 06b4  Dell Latitude
10ec  Realtek Semiconductor Co., Ltd.
\t8168  RTL8111/8168/8411 PCI Express Gigabit Ethernet
C 02  Network controller
\t00  Ethernet controller
"""


def usb_modalias(vid, pid, ic, isc, ip):
    return f"usb:v{vid.upper()}p{pid.upper()}d0100dc00dsc00dp00ic{ic:02X}isc{isc:02X}ip{ip:02X}in00"


def pci_modalias(vid, did, bc, sc, i=0):
    return f"pci:v0000{vid.upper()}d0000{did.upper()}sv00001028sd000006B4bc{bc:02X}sc{sc:02X}i{i:02X}"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def can_symlink() -> bool:
    with tempfile.TemporaryDirectory() as d:
        try:
            os.symlink(d, os.path.join(d, "l"))
            return True
        except (OSError, NotImplementedError):
            return False


def dev(**kw):
    base = dict(id="x", name="X", vendor="V", vendor_id="abcd", product_id="0001", category="wifi", bus="usb", sys_id="1-1", modalias="usb:x")
    base.update(kw)
    return HardwareDevice(**base)
