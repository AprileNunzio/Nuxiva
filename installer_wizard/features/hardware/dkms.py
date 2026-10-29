from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from features.hardware.validation import MODULE

from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("nuxiva.hardware.dkms")

RunCmd = Callable[..., Awaitable[Tuple[int, str]]]
INSTALL_TIMEOUT = 1200
GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "0"}


ALLOWED_GIT_REPOSITORIES = {"https://github.com/aircrack-ng/rtl8812au.git", "https://github.com/morrownr/8821cu-20210916.git", "https://github.com/morrownr/88x2bu-20210702.git"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+\-]{0,63}$")

TOOLCHAIN = {
    "apt": ["dkms", "build-essential"],
    "dnf": ["dkms", "gcc", "make", "elfutils-libelf-devel"],
    "pacman": ["dkms", "base-devel"],
    "zypper": ["dkms", "gcc", "make"],
}


@dataclass
class DkmsResult:
    ok: bool = False
    module: str = ""
    dkms_name: str = ""
    dkms_version: str = ""
    message: str = ""
    log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "module": self.module,
            "dkms_name": self.dkms_name,
            "dkms_version": self.dkms_version,
            "message": self.message,
        }


def parse_dkms_conf(text: str) -> Tuple[str, str]:

    values: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r'^\s*(PACKAGE_NAME|PACKAGE_VERSION)\s*=\s*["\']?([^"\'\s#]+)', line)
        if m:
            values[m.group(1)] = m.group(2)
    return values.get("PACKAGE_NAME", ""), values.get("PACKAGE_VERSION", "")


def validate_git_url(url: str) -> bool:
    return url in ALLOWED_GIT_REPOSITORIES


def kernel_release() -> str:
    try:
        return os.uname().release
    except AttributeError:
        return ""


def headers_packages(pkg_manager: str, distro_family: str, release: str) -> List[str]:

    if pkg_manager == "apt":
        if distro_family == "ubuntu":
            return [f"linux-headers-{release}", "linux-headers-generic"]
        return [f"linux-headers-{release}", "linux-headers-amd64"]
    if pkg_manager in ("dnf", "yum"):
        return [f"kernel-devel-{release}", "kernel-devel"]
    if pkg_manager == "pacman":
        return ["linux-headers"]
    if pkg_manager == "zypper":
        return ["kernel-default-devel"]
    return []


def headers_present(release: Optional[str] = None) -> bool:
    rel = release or kernel_release()
    return bool(rel) and Path(f"/lib/modules/{rel}/build").exists()


class DkmsBroker:
    def __init__(
        self,
        run_cmd: RunCmd,
        install_packages: Callable[[List[str]], Awaitable[Tuple[int, str]]],
        src_root: Path = Path("/usr/src"),
    ) -> None:
        self._run = run_cmd
        self._install = install_packages
        self._src_root = src_root

    async def ensure_toolchain(self, pkg_manager: str, distro_family: str) -> Tuple[bool, str]:

        key = "dnf" if pkg_manager == "yum" else pkg_manager
        tools = TOOLCHAIN.get(key)
        if tools is None:
            return False, f"Gestore pacchetti {pkg_manager} non supportato per DKMS"
        missing = []
        if not shutil.which("dkms"):
            missing.extend(tools)
        elif not shutil.which("gcc") or not shutil.which("make"):
            missing.extend(t for t in tools if t != "dkms")
        if missing:
            code, out = await self._install(list(dict.fromkeys(missing)))
            if code != 0:
                return False, f"Toolchain DKMS non installata: {out[-200:]}"
        rel = kernel_release()
        if not _SAFE_NAME.fullmatch(rel):
            return False, "Invalid running kernel release"
        if not headers_present(rel):
            last_out = ""
            for candidate in headers_packages(pkg_manager, distro_family, rel):
                code, last_out = await self._install([candidate])
                if code == 0 and headers_present(rel):
                    break
            else:
                return False, f"Header del kernel {rel} non disponibili: {last_out[-200:]}"
        return True, "toolchain pronta"

    async def status(self) -> List[str]:
        code, out = await self._run(["dkms", "status"], timeout=30)
        return out.splitlines() if code == 0 else []

    async def is_installed(self, dkms_name: str) -> bool:
        return any(line.startswith(dkms_name) and "installed" in line for line in await self.status())

    async def install_from_git(self, spec: Dict[str, Any]) -> DkmsResult:
        result = DkmsResult(module=str(spec.get("module", "")))
        url, revision = str(spec.get("git", "")), str(spec.get("revision", ""))
        if not validate_git_url(url) or not re.fullmatch(r"[0-9a-f]{40}", revision) or not MODULE.fullmatch(result.module):
            result.message = "Untrusted or unpinned driver source"
            return result
        release = kernel_release()
        if not _SAFE_NAME.fullmatch(release):
            result.message = "Invalid running kernel release"
            return result
        if not await secure_boot_permits_sources(self._run):
            result.message = "Secure Boot requires a separately enrolled trusted module signing key"
            return result
        workdir = Path(tempfile.mkdtemp(prefix="nuxiva-dkms-"))
        src, destination = workdir / "src", None
        created, registered, completed = False, False, False
        try:
            commands = [
                ["git", "init", str(src)],
                ["git", "-C", str(src), "remote", "add", "origin", url],
                ["git", "-c", "http.followRedirects=false", "-c", "core.hooksPath=" + os.devnull,
                 "-C", str(src), "fetch", "--depth", "1", "origin", revision],
                ["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(src), "checkout", "--detach", "FETCH_HEAD"],
            ]
            for command in commands:
                code, output = await self._run(command, timeout=300, env=GIT_ENV)
                if code:
                    result.message = "Source retrieval failed: " + output[-200:]
                    return result
            code, actual = await self._run(["git", "-C", str(src), "rev-parse", "HEAD"], timeout=30, env=GIT_ENV)
            if code or actual.strip() != revision:
                result.message = "Source revision mismatch"
                return result
            if any(path.is_symlink() for path in src.rglob("*")):
                result.message = "Source symlinks refused"
                return result
            name, version = parse_dkms_conf((src / "dkms.conf").read_text(encoding="utf-8"))
            if not (_SAFE_NAME.fullmatch(name) and _SAFE_NAME.fullmatch(version)):
                result.message = "Invalid DKMS package metadata"
                return result
            result.dkms_name, result.dkms_version = name, version
            destination = self._src_root / f"{name}-{version}"
            marker = destination / ".nuxiva-revision"
            if destination.is_dir() and not destination.is_symlink() and marker.is_file() and not marker.is_symlink() and marker.read_text(encoding="utf-8") == revision:
                code, output = await self._run(["dkms", "status", "-m", name, "-v", version, "-k", release], timeout=30)
                if code == 0 and any("installed" in line for line in output.splitlines()):
                    result.ok = True
                    result.message = "Pinned driver already installed for running kernel"
                    return result
            if self._src_root.is_symlink() or destination.exists() or destination.is_symlink():
                result.message = "Existing driver sources preserved; replacement requires managed migration"
                return result
            destination.mkdir()
            created = True
            shutil.copytree(src, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
            marker.write_text(revision, encoding="utf-8")
            for step in ("add", "build", "install"):
                command = ["dkms", step, "-m", name, "-v", version]
                if step != "add":
                    command += ["-k", release]
                code, output = await self._run(command, timeout=INSTALL_TIMEOUT)
                result.log.append(output[-600:])
                if code:
                    result.message = f"dkms {step} fallito: {output[-240:]}"
                    return result
                if step == "add":
                    registered = True
            code, output = await self._run(["dkms", "status", "-m", name, "-v", version, "-k", release], timeout=30)
            if code or not any("installed" in line for line in output.splitlines()):
                result.message = "DKMS installation verification failed"
                return result
            result.ok, completed = True, True
            result.message = f"Driver {name} {version} installed for {release}"
            return result
        except (OSError, ValueError, shutil.Error) as exc:
            log.error("DKMS source integration failed: %s", exc)
            result.message = str(exc)
            return result
        finally:
            if not completed and registered:
                code, output = await asyncio.shield(self._run(
                    ["dkms", "remove", "-m", result.dkms_name, "-v", result.dkms_version, "--all"], timeout=120))
                if code:
                    log.error("DKMS rollback failed: %s", output[-300:])
                    created = False
                    result.message += "; rollback failed, sources retained"
            if not completed and created:
                shutil.rmtree(destination)
            shutil.rmtree(workdir)


async def secure_boot_permits_sources(run):
    if not Path("/sys/firmware/efi").exists():
        return True
    code, output = await run(["mokutil", "--sb-state"], timeout=20)
    return code == 0 and "SecureBoot disabled" in output
