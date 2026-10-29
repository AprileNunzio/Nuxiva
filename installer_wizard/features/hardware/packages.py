import logging
from typing import Dict, List, Tuple

from features.hardware.validation import packages_valid

log = logging.getLogger("nuxiva.hardware.packages")


class PackageOperations:
    async def update_packages(self) -> Tuple[int, str]:
        pkg_mgr = self.detect_pkg_manager()
        log.info("Agente Hardware: Aggiornamento sorgenti pacchetti tramite %s", pkg_mgr)
        if pkg_mgr == "apt":
            return await self._run_cmd(["apt-get", "-o", "Acquire::AllowInsecureRepositories=false", "update"], timeout=240)
        elif pkg_mgr in ("yum", "dnf"):
            return await self._run_cmd([pkg_mgr, "makecache"], timeout=240)
        elif pkg_mgr == "zypper":
            return await self._run_cmd(["zypper", "refresh"], timeout=240)
        elif pkg_mgr == "pacman":
            return 1, "Rolling-release upgrades require an administrator-managed full transaction"
        return 1, "No supported package manager"

    async def filter_available(self, packages: List[str]) -> Tuple[List[str], List[str]]:


        if not packages_valid(packages):
            return [], list(packages)
        if self.detect_pkg_manager() != "apt" or not packages:
            return list(packages), []
        code, out = await self._run_cmd(["apt-cache", "policy", *packages], timeout=60)
        if code != 0:
            return [], list(packages)
        available: Dict[str, bool] = {}
        current = ""
        for line in out.splitlines():
            if line and not line.startswith(" ") and line.rstrip().endswith(":"):
                current = line.rstrip()[:-1]
                available[current] = False
            elif current and line.strip().startswith("Candidate:"):
                available[current] = line.split(":", 1)[1].strip() != "(none)"
        ok = [p for p in packages if available.get(p)]
        skipped = [p for p in packages if not available.get(p)]
        return ok, skipped

    async def install_packages(self, packages: List[str]) -> Tuple[int, str]:
        if not packages_valid(packages):
            return 1, "Invalid package identifiers"
        if not packages:
            return 0, "Nessun pacchetto richiesto"
        pkg_mgr = self.detect_pkg_manager()
        log.info("Agente Hardware: Installazione driver/pacchetti %s tramite %s", packages, pkg_mgr)
        if pkg_mgr == "apt":
            cmd = ["apt-get", "-o", "APT::Get::AllowUnauthenticated=false", "-o", "Acquire::AllowInsecureRepositories=false", "install", "-y", "--no-install-recommends", *packages]
        elif pkg_mgr in ("yum", "dnf"):
            cmd = [pkg_mgr, "install", "-y", *packages]
        elif pkg_mgr == "zypper":
            cmd = ["zypper", "--non-interactive", "install", *packages]
        elif pkg_mgr == "pacman":
            return 1, "Rolling-release upgrades require an administrator-managed full transaction"
        else:
            return 1, "Package manager non supportato per installazione automatica"
        return await self._run_cmd(cmd, timeout=900)
