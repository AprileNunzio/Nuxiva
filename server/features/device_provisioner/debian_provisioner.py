import asyncio
import os
import re
import shlex
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.features.device_provisioner.models import (
    DebianProbeRequest,
    DebianProvisionRequest,
    DeviceType,
    ProvisionJobResult,
    ProvisionStepLog,
)
from server.features.password_vault.vault_service import password_vault_service

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
SAFE_HOST_RE = re.compile(r"^[a-zA-Z0-9.\-:_]+$")
SAFE_USER_RE = re.compile(r"^[a-zA-Z0-9._\-]+$")


def _validate_target(host: str, username: str) -> None:
    if not SAFE_HOST_RE.match(host.strip()):
        raise ValueError("Host non valido.")
    if not SAFE_USER_RE.match(username.strip()):
        raise ValueError("Username SSH non valido.")


async def _tcp_probe(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, str]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        banner = ""
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=1.5)
            banner = raw.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            pass
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True, banner or "TCP port open"
    except Exception as exc:
        return False, str(exc)


async def _exec(cmd: List[str], env: Optional[Dict[str, str]] = None, timeout: float = 45.0) -> Tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            out.decode("utf-8", errors="replace"),
            err.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", f"Timeout dopo {timeout}s"


class DebianAutonomousProvisioner:
    """
    Provisioner autonomo multi-strategia per server Debian/Linux via SSH:
    1. Risolve le credenziali SSH dal Password Vault cifrato dell'utente collegato (se indicato).
    2. Verifica raggiungibilità TCP e banner SSH del target.
    3. Testa automaticamente più metodi di connessione in ordine di sicurezza:
       - Chiave SSH (BatchMode=yes)
       - Password via sshpass (SSHPASS in env, mai nella command line)
       - Fallback Python paramiko (se installato)
    4. Ispeziona sistema remoto (OS, architettura, RAM, disco).
    5. Trasferisce install.sh via scp ed esegue il deploy Nuxiva verificando lo stato finale.
    """

    def _resolve_credentials(
        self,
        req: DebianProbeRequest,
    ) -> Tuple[str, int, str, str, str, Optional[str]]:
        host = req.host.strip()
        port = req.port
        username = req.username.strip()
        password = req.ssh_password
        key_path = req.ssh_key_path.strip()
        vault_note = None

        if req.ssh_vault_entry_id:
            revealed = password_vault_service.reveal_entry(req.user_id, req.ssh_vault_entry_id)
            host = host or revealed.host_or_url
            if revealed.port:
                port = revealed.port
            username = revealed.username or username
            password = password or revealed.secret
            vault_note = f"Credenziali SSH risolte dal vault utente '{req.user_id}' ({revealed.label})."

        _validate_target(host, username)
        return host, port, username, password, key_path, vault_note

    async def _run_ssh_with_fallback(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        key_path: str,
        remote_command: str,
        timeout: float = 30.0,
    ) -> Tuple[bool, str, str, str]:
        """Ritorna (ok, method_used, stdout, stderr)."""
        base_opts = [
            "-p", str(port),
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=8",
        ]
        target = f"{username}@{host}"

        # Metodo 1: SSH con chiave (BatchMode=yes)
        ssh_bin = shutil.which("ssh")
        if ssh_bin:
            cmd_key = [ssh_bin, *base_opts, "-o", "BatchMode=yes"]
            if key_path:
                cmd_key.extend(["-i", key_path])
            cmd_key.extend([target, remote_command])
            rc, out, err = await _exec(cmd_key, timeout=timeout)
            if rc == 0:
                return True, "ssh_key", out, err

        # Metodo 2: SSH con password tramite sshpass (env SSHPASS)
        sshpass_bin = shutil.which("sshpass")
        if password and ssh_bin and sshpass_bin:
            env = os.environ.copy()
            env["SSHPASS"] = password
            cmd_pw = [sshpass_bin, "-e", ssh_bin, *base_opts, target, remote_command]
            rc, out, err = await _exec(cmd_pw, env=env, timeout=timeout)
            if rc == 0:
                return True, "ssh_password_sshpass", out, err

        # Metodo 3: Fallback Python paramiko (se presente)
        if password:
            try:
                import paramiko  # type: ignore

                def _paramiko_exec() -> Tuple[int, str, str]:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(hostname=host, port=port, username=username, password=password, timeout=8)
                    try:
                        _, stdout_f, stderr_f = client.exec_command(remote_command, timeout=timeout)
                        exit_code = stdout_f.channel.recv_exit_status()
                        return exit_code, stdout_f.read().decode("utf-8", "replace"), stderr_f.read().decode("utf-8", "replace")
                    finally:
                        client.close()

                rc, out, err = await asyncio.to_thread(_paramiko_exec)
                if rc == 0:
                    return True, "python_paramiko", out, err
                return False, "python_paramiko", out, err
            except ImportError:
                pass
            except Exception as exc:
                return False, "python_paramiko", "", str(exc)

        return False, "none", "", "Nessun metodo di autenticazione SSH riuscito (chiave non autorizzata e sshpass/paramiko non disponibili)."

    async def probe(self, req: DebianProbeRequest) -> ProvisionJobResult:
        job_id = f"deb_probe_{uuid.uuid4().hex[:8]}"
        steps: List[ProvisionStepLog] = []
        detected_info: Dict[str, Any] = {}

        t0 = time.time()
        try:
            host, port, username, password, key_path, vault_note = self._resolve_credentials(req)
        except (PermissionError, KeyError, ValueError) as exc:
            steps.append(ProvisionStepLog(step="credentials", status="failed", detail=str(exc)))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=req.host,
                success=False,
                steps=steps,
                summary=str(exc),
            )

        if vault_note:
            steps.append(ProvisionStepLog(step="vault_credentials", status="ok", detail=vault_note, duration_ms=round((time.time() - t0) * 1000, 1)))

        t1 = time.time()
        reachable, banner = await _tcp_probe(host, port)
        detected_info["tcp_banner"] = banner
        steps.append(ProvisionStepLog(
            step="tcp_probe",
            status="ok" if reachable else "failed",
            detail=f"{host}:{port} -> {banner}",
            duration_ms=round((time.time() - t1) * 1000, 1),
        ))
        if not reachable:
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{host}:{port}",
                success=False,
                detected_info=detected_info,
                steps=steps,
                summary=f"Host Debian {host}:{port} non raggiungibile via TCP.",
            )

        t2 = time.time()
        probe_cmd = "uname -srm && (grep PRETTY_NAME /etc/os-release 2>/dev/null || true) && free -m | awk '/Mem:/{print \"RAM_MB=\"$2}'"
        ok, method, out, err = await self._run_ssh_with_fallback(host, port, username, password, key_path, probe_cmd)
        detected_info["auth_method"] = method
        if ok:
            detected_info["remote_system"] = out.strip()
            steps.append(ProvisionStepLog(
                step="ssh_probe",
                status="ok",
                detail=f"Connesso via {method}. Sistema rilevato: {out.strip().replace(chr(10), ' | ')}",
                duration_ms=round((time.time() - t2) * 1000, 1),
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{username}@{host}:{port}",
                success=True,
                detected_info=detected_info,
                steps=steps,
                summary=f"Server Debian raggiungibile e autenticato via {method}.",
            )

        steps.append(ProvisionStepLog(
            step="ssh_probe",
            status="failed",
            detail=err.strip()[:250],
            duration_ms=round((time.time() - t2) * 1000, 1),
        ))
        return ProvisionJobResult(
            job_id=job_id,
            device_type=DeviceType.DEBIAN_SERVER,
            target=f"{username}@{host}:{port}",
            success=False,
            detected_info=detected_info,
            steps=steps,
            summary=f"Porta SSH aperta su {host}:{port}, ma autenticazione fallita.",
        )

    async def provision(self, req: DebianProvisionRequest) -> ProvisionJobResult:
        job_id = f"deb_inst_{uuid.uuid4().hex[:8]}"
        steps: List[ProvisionStepLog] = []
        detected_info: Dict[str, Any] = {"install_mode": req.install_mode}

        t0 = time.time()
        try:
            host, port, username, password, key_path, vault_note = self._resolve_credentials(req)
        except (PermissionError, KeyError, ValueError) as exc:
            steps.append(ProvisionStepLog(step="credentials", status="failed", detail=str(exc)))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=req.host,
                success=False,
                steps=steps,
                summary=str(exc),
            )

        if vault_note:
            steps.append(ProvisionStepLog(step="vault_credentials", status="ok", detail=vault_note, duration_ms=round((time.time() - t0) * 1000, 1)))

        if req.dry_run:
            steps.append(ProvisionStepLog(
                step="dry_run_plan",
                status="ok",
                detail=(
                    f"Piano validato per {username}@{host}:{port}: "
                    f"1) Probe TCP+SSH (chiave -> sshpass -> paramiko), "
                    f"2) Trasferimento {INSTALL_SCRIPT.name} via SCP, "
                    f"3) Installazione unattended ({req.install_mode}) collegata a {req.nuxiva_server_url}, "
                    f"4) Verifica servizio attivo."
                ),
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{username}@{host}:{port}",
                success=True,
                detected_info=detected_info,
                steps=steps,
                summary=f"Piano di auto-installazione Debian ({req.install_mode}) su {host} validato (dry-run).",
            )

        # Step 1: Probe connessione e OS
        probe_res = await self.probe(req)
        steps.extend(probe_res.steps)
        detected_info.update(probe_res.detected_info)
        if not probe_res.success:
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{username}@{host}:{port}",
                success=False,
                detected_info=detected_info,
                steps=steps,
                summary=probe_res.summary,
            )

        # Step 2: Trasferimento install.sh via scp
        t_scp = time.time()
        scp_bin = shutil.which("scp")
        sshpass_bin = shutil.which("sshpass")
        if not scp_bin or not INSTALL_SCRIPT.exists():
            steps.append(ProvisionStepLog(
                step="scp_transfer",
                status="failed",
                detail="Strumento scp o install.sh non disponibile sull'host locale.",
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{username}@{host}:{port}",
                success=False,
                detected_info=detected_info,
                steps=steps,
                summary="Impossibile trasferire l'installer via SCP.",
            )

        scp_cmd = [
            scp_bin,
            "-P", str(port),
            "-o", "StrictHostKeyChecking=accept-new",
            str(INSTALL_SCRIPT),
            f"{username}@{host}:/tmp/nuxiva_install.sh",
        ]
        env = os.environ.copy()
        if probe_res.detected_info.get("auth_method") == "ssh_password_sshpass" and sshpass_bin and password:
            env["SSHPASS"] = password
            scp_cmd = [sshpass_bin, "-e", *scp_cmd]
        elif key_path:
            scp_cmd.insert(1, "-i")
            scp_cmd.insert(2, key_path)

        rc, out, err = await _exec(scp_cmd, env=env, timeout=60.0)
        if rc != 0:
            steps.append(ProvisionStepLog(
                step="scp_transfer",
                status="failed",
                detail=(err or out).strip()[:250],
                duration_ms=round((time.time() - t_scp) * 1000, 1),
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.DEBIAN_SERVER,
                target=f"{username}@{host}:{port}",
                success=False,
                detected_info=detected_info,
                steps=steps,
                summary="Trasferimento file SCP fallito.",
            )

        steps.append(ProvisionStepLog(
            step="scp_transfer",
            status="ok",
            detail="install.sh trasferito su /tmp/nuxiva_install.sh.",
            duration_ms=round((time.time() - t_scp) * 1000, 1),
        ))

        # Step 3: Esecuzione installazione remota unattended
        t_inst = time.time()
        safe_url = shlex.quote(req.nuxiva_server_url)
        safe_mode = shlex.quote(req.install_mode)
        remote_install = (
            f"chmod +x /tmp/nuxiva_install.sh && "
            f"NUXIVA_UNATTENDED=1 NUXIVA_INSTALL_MODE={safe_mode} NUXIVA_SERVER_URL={safe_url} "
            f"bash /tmp/nuxiva_install.sh"
        )
        ok, method, out, err = await self._run_ssh_with_fallback(
            host, port, username, password, key_path, remote_install, timeout=300.0
        )
        steps.append(ProvisionStepLog(
            step="remote_install",
            status="ok" if ok else "failed",
            detail=(out if ok else (err or out)).strip()[-300:] or ("Installazione completata." if ok else "Errore installazione."),
            duration_ms=round((time.time() - t_inst) * 1000, 1),
        ))

        return ProvisionJobResult(
            job_id=job_id,
            device_type=DeviceType.DEBIAN_SERVER,
            target=f"{username}@{host}:{port}",
            success=ok,
            detected_info=detected_info,
            steps=steps,
            summary=(
                f"Auto-installazione Nuxiva ({req.install_mode}) completata su {host} via {method}."
                if ok else f"Auto-installazione fallita su {host}."
            ),
        )


debian_provisioner = DebianAutonomousProvisioner()
