import os
from typing import Dict, Any
from .base import RemoteProtocol
from server.features.remote_control.utils import ensure_dependency

class BaseUnixSSHProtocol(RemoteProtocol):
    def __init__(self, hostname: str, username: str, key_path: str = None, password: str = None):
        ensure_dependency("asyncssh", "asyncssh")
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.password = password
        
    async def _run(self, cmd: str) -> str:
        import asyncssh
        client_keys = [self.key_path] if self.key_path and os.path.exists(self.key_path) else None
        async with asyncssh.connect(
            self.hostname,
            username=self.username,
            password=self.password or None,
            client_keys=client_keys,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd, check=True)
            return result.stdout

    async def _safe_exec(self, cmd: str) -> Dict[str, Any]:
        try:
            return {"status": "success", "data": await self._run(cmd)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        return await self._safe_exec("uname -a && uptime && (cat /etc/os-release | grep PRETTY_NAME || true)")

    async def check_updates(self) -> Dict[str, Any]:
        return await self._safe_exec("apt list --upgradable 2>/dev/null || yum check-update 2>/dev/null || echo 'Nessun aggiornamento pendente'")

    async def get_cpu_usage(self) -> Dict[str, Any]:
        return await self._safe_exec("top -bn1 | head -n 5 || uptime")

    async def restart_service(self, service_name: str) -> Dict[str, Any]:
        return await self._safe_exec(f"sudo systemctl restart '{service_name}'")

    async def reboot_system(self, force: bool = False) -> Dict[str, Any]:
        return await self._safe_exec("sudo shutdown -r +1 || sudo reboot")

    async def list_active_users(self) -> Dict[str, Any]:
        return await self._safe_exec("who")

    async def get_network_info(self) -> Dict[str, Any]:
        return await self._safe_exec("ip -4 a || ifconfig")

    async def get_disk_space(self) -> Dict[str, Any]:
        return await self._safe_exec("df -h")
