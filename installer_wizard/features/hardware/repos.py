from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid

from features.hardware.apt_sources import source_lines as enable_components_in_sources, deb822 as enable_components_in_deb822, active_components
from features.hardware.atomic import write_text
from features.hardware.rpm_repositories import ensure_repositories
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("nuxiva.hardware.repos")

RunCmd = Callable[..., Awaitable[Tuple[int, str]]]

DEBIAN_HOST_HINTS = ("debian.org", "debian.net")
UBUNTU_HOST_HINTS = ("ubuntu.com", "archive.ubuntu", "ports.ubuntu")

UBUNTU_EQUIV = {"non-free": "multiverse", "contrib": "universe", "non-free-firmware": None}
VALID_COMPONENTS = ("contrib", "non-free", "non-free-firmware")


@dataclass
class OsInfo:
    distro_id: str = ""
    id_like: List[str] = field(default_factory=list)
    version_id: str = ""

    @property
    def family(self) -> str:
        ids = [self.distro_id, *self.id_like]
        if "ubuntu" in ids:
            return "ubuntu"
        if "debian" in ids:
            return "debian"
        if self.distro_id == "fedora":
            return "fedora"
        if any(i in ids for i in ("rhel", "centos", "rocky", "almalinux")):
            return "rhel"
        if "fedora" in ids:
            return "fedora"
        if "arch" in ids:
            return "arch"
        if any(i in ids for i in ("suse", "opensuse", "sles")):
            return "suse"
        return "unknown"

    @property
    def major(self) -> int:
        m = re.match(r"(\d+)", self.version_id or "")
        return int(m.group(1)) if m else 0


def read_os_release(path: str = "/etc/os-release") -> OsInfo:
    info = OsInfo()
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
            key, _, value = line.partition("=")
            value = value.strip().strip('"')
            if key == "ID":
                info.distro_id = value.lower()
            elif key == "ID_LIKE":
                info.id_like = value.lower().split()
            elif key == "VERSION_ID":
                info.version_id = value
    except OSError:
        pass
    return info


@dataclass
class RepoResult:
    changed: bool = False
    enabled: List[str] = field(default_factory=list)
    already: List[str] = field(default_factory=list)
    unsupported: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    backups: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    ok: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "changed": self.changed,
            "enabled": self.enabled,
            "already": self.already,
            "unsupported": self.unsupported,
            "files": self.files,
            "backups": self.backups,
            "notes": self.notes,
            "ok": self.ok,
        }


def map_components(components: List[str], os_info: OsInfo) -> Tuple[List[str], List[str]]:


    wanted: List[str] = []
    skipped: List[str] = []
    for comp in components:
        if comp not in VALID_COMPONENTS:
            continue
        if os_info.family == "ubuntu":
            mapped = UBUNTU_EQUIV.get(comp)
            if mapped:
                if mapped not in wanted:
                    wanted.append(mapped)
            else:
                skipped.append(comp)
        elif os_info.family == "debian":
            if comp == "non-free-firmware" and 0 < os_info.major < 12:
                skipped.append(comp)
            elif comp not in wanted:
                wanted.append(comp)
    return wanted, skipped


class RepoManager:
    def __init__(
        self,
        run_cmd: RunCmd,
        os_info: Optional[OsInfo] = None,
        apt_dir: str = "/etc/apt",
    ) -> None:
        self._run = run_cmd
        self.os_info = os_info or read_os_release()
        self._apt_dir = Path(apt_dir)
        self._written = {}


    def _apt_files(self) -> List[Path]:
        files: List[Path] = []
        main = self._apt_dir / "sources.list"
        if main.is_file():
            files.append(main)
        d = self._apt_dir / "sources.list.d"
        if d.is_dir():
            files.extend(sorted(d.glob("*.sources")))
            files.extend(sorted(d.glob("*.list")))
        return files

    def apt_status(self) -> Dict[str, bool]:

        present: set = set()
        for f in self._apt_files():
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            present.update(active_components(content, f.suffix, self.os_info))
        return {c: c in present for c in (*VALID_COMPONENTS, "universe", "multiverse")}

    def _enable_apt(self, components: List[str]) -> RepoResult:
        result = RepoResult()
        wanted, skipped = map_components(components, self.os_info)
        result.unsupported.extend(skipped)
        if not wanted:
            return result
        stamp = time.strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().int)[:10]
        files = self._apt_files()
        if not files:
            result.ok = False
            result.notes.append("No APT source files")
        for path in files:
            if path.is_symlink() or not path.resolve().is_relative_to(self._apt_dir.resolve()):
                result.ok = False
                result.notes.append(f"Symlink refused: {path}")
                continue
            try:
                original = path.read_text(encoding="utf-8")
            except OSError as exc:
                result.ok = False
                result.notes.append(str(exc))
                continue
            if path.suffix == ".sources":
                new, added = enable_components_in_deb822(original, wanted, self.os_info)
            else:
                new, added = enable_components_in_sources(original, wanted, self.os_info)
            if not added:
                continue
            backup = path.with_name(path.name + f".nuxiva-bak-{stamp}")
            try:
                write_text(backup, original)
                if path.read_text(encoding="utf-8") != original:
                    raise OSError("APT configuration changed during preparation")
                write_text(path, new)
            except OSError as exc:
                result.ok = False
                result.notes.append(f"{path}: scrittura non riuscita ({exc})")
                continue
            self._written[str(backup)] = hashlib.sha256(new.encode("utf-8")).hexdigest()
            result.changed = True
            result.files.append(str(path))
            result.backups.append(str(backup))
            for c in added:
                if c not in result.enabled:
                    result.enabled.append(c)
        status = self.apt_status()
        result.already = [c for c in wanted if c not in result.enabled and status.get(c)]
        if any(not status.get(c) for c in wanted):
            result.ok = False
            result.notes.append("Required components are not enabled")
        return result


    async def _enable_dnf(self, components: List[str]) -> RepoResult:
        if not any(component in ("non-free", "contrib") for component in components):
            return RepoResult()
        return await ensure_repositories(self._run, self.os_info, RepoResult())


    async def ensure(self, components: List[str], pkg_manager: str) -> RepoResult:

        components = [c for c in components if c in VALID_COMPONENTS]
        if not components:
            return RepoResult()
        if pkg_manager == "apt" and self.os_info.family in ("debian", "ubuntu"):
            return self._enable_apt(components)
        if pkg_manager in ("dnf", "yum"):
            return await self._enable_dnf(components)
        result = RepoResult()
        result.ok = False
        result.unsupported.extend(components)
        result.notes.append(f"Abilitazione repository non automatizzata per {pkg_manager}/{self.os_info.family}")
        return result

    def restore(self, backups: List[str]) -> List[str]:

        restored: List[str] = []
        for b in backups:
            bp = Path(b)
            if bp.is_symlink() or not bp.resolve().is_relative_to(self._apt_dir.resolve()):
                raise ValueError("Repository backup outside managed directory")
            m = re.match(r"(.+)\.nuxiva-bak-\d+$", bp.name)
            if not m or not bp.is_file():
                continue
            target = bp.with_name(m.group(1))
            expected = self._written.get(str(bp))
            if expected is None or target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                log.error("Repository rollback refused: current configuration differs from managed write (%s)", target)
                continue
            try:
                write_text(target, bp.read_text(encoding="utf-8"))
                restored.append(str(target))
            except OSError as exc:
                log.warning("Ripristino %s non riuscito: %s", target, exc)
        return restored
