from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("nuxiva.store.sandbox_bridge")

try:
    from server.features.sandbox.domain.spec import valid_egress_host
    HAS_SANDBOX_DOMAIN = True
except (ImportError, ModuleNotFoundError, Exception):
    HAS_SANDBOX_DOMAIN = False


class PackageSandboxProfile:
    def __init__(
        self,
        package_id: str,
        network_policy: str,
        allowed_hosts: list[str],
        memory_mb: int,
        cpus: float,
        pids: int,
        wall_seconds: int,
    ) -> None:
        self.package_id = package_id
        self.network_policy = network_policy
        self.allowed_hosts = allowed_hosts
        self.memory_mb = memory_mb
        self.cpus = cpus
        self.pids = pids
        self.wall_seconds = wall_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "network_policy": self.network_policy,
            "allowed_hosts": self.allowed_hosts,
            "resource_limits": {
                "memory_mb": self.memory_mb,
                "cpus": self.cpus,
                "pids": self.pids,
                "wall_seconds": self.wall_seconds,
            },
        }


def build_sandbox_profile_for_package(pkg: dict[str, Any]) -> PackageSandboxProfile:
    pkg_id = str(pkg.get("id") or "untrusted_package")
    declared_hosts = list(pkg.get("allowed_hosts") or [])
    capabilities = set(pkg.get("capabilities") or [])

    safe_hosts: list[str] = []
    if "network_fetch" in capabilities or "network" in capabilities:
        for host in declared_hosts:
            cleaned = str(host).strip().lower()
            if HAS_SANDBOX_DOMAIN:
                if valid_egress_host(cleaned):
                    safe_hosts.append(cleaned)
                else:
                    log.warning("Host egress non valido scartato (%s): %s", pkg_id, cleaned)
            else:
                if cleaned and "." in cleaned and not cleaned.startswith("."):
                    safe_hosts.append(cleaned)

    policy = "allowlist" if safe_hosts else "none"

    size_gb = float(pkg.get("size_gb", 0.5))
    computed_mem_mb = max(64, min(1024, int(size_gb * 512)))

    cpus = 1.0 if size_gb >= 2.0 else 0.5
    pids = 128 if size_gb >= 2.0 else 64
    wall_seconds = 180 if size_gb >= 2.0 else 60

    return PackageSandboxProfile(
        package_id=pkg_id,
        network_policy=policy,
        allowed_hosts=safe_hosts,
        memory_mb=computed_mem_mb,
        cpus=cpus,
        pids=pids,
        wall_seconds=wall_seconds,
    )
