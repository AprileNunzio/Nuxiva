import asyncio
import glob
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.features.device_provisioner.models import (
    DeviceType,
    Esp32ProvisionRequest,
    ProvisionJobResult,
    ProvisionStepLog,
    SerialPortCandidate,
)
from server.features.password_vault.vault_service import password_vault_service

ESP32_USB_SIGNATURES: Dict[str, str] = {
    "10C4:EA60": "Silicon Labs CP210x (ESP32 DevKit)",
    "1A86:7523": "WCH CH340 (ESP32)",
    "1A86:55D4": "WCH CH9102 (ESP32-S2/S3/C3)",
    "0403:6001": "FTDI FT232R (ESP32)",
    "0403:6010": "FTDI FT2232 (ESP32 JTAG/UART)",
    "303A:1001": "Espressif Native USB JTAG/Serial (ESP32-S3/C3)",
    "303A:0002": "Espressif ESP32-S2 Native USB",
}

ESP32_PROJECT_DIR = Path(__file__).resolve().parents[3] / "client_satellite" / "microcontrollers" / "esp32"


def _classify_usb_ids(vid_hex: Optional[str], pid_hex: Optional[str], desc: str = "") -> Tuple[str, bool]:
    if vid_hex and pid_hex:
        key = f"{vid_hex.upper()}:{pid_hex.upper()}"
        if key in ESP32_USB_SIGNATURES:
            return ESP32_USB_SIGNATURES[key], True
        if vid_hex.upper() == "303A":
            return "Espressif Native USB", True
    lower = desc.lower()
    if any(tok in lower for tok in ("cp210", "ch340", "ch9102", "espressif", "esp32", "usb serial")):
        return desc or "USB-UART Serial", True
    return "Generic Serial", False


def discover_serial_ports() -> List[SerialPortCandidate]:
    """
    Scansiona automaticamente le porte seriali/COM (Windows & Linux) per identificare ESP32 collegati.
    Usa pyserial se presente, con fallback nativo su /dev/ttyUSB*, /dev/ttyACM* e sysfs su Linux.
    """
    candidates: List[SerialPortCandidate] = []
    seen = set()

    try:
        import serial.tools.list_ports as list_ports  # type: ignore

        for p in list_ports.comports():
            vid = f"{p.vid:04X}" if p.vid is not None else None
            pid = f"{p.pid:04X}" if p.pid is not None else None
            hint, likely = _classify_usb_ids(vid, pid, p.description or "")
            candidates.append(
                SerialPortCandidate(
                    port=p.device,
                    description=p.description or "",
                    hwid=p.hwid or "",
                    vid=vid,
                    pid=pid,
                    chip_hint=hint,
                    is_esp32_likely=likely,
                )
            )
            seen.add(p.device)
    except ImportError:
        pass

    # Fallback nativo Linux (/dev/ttyUSB*, /dev/ttyACM*)
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*"):
        for dev in sorted(glob.glob(pattern)):
            if dev in seen:
                continue
            tty_name = os.path.basename(dev)
            vid, pid = _read_linux_sysfs_usb_ids(tty_name)
            hint, likely = _classify_usb_ids(vid, pid, tty_name)
            candidates.append(
                SerialPortCandidate(
                    port=dev,
                    description=f"Linux USB Serial ({tty_name})",
                    hwid=f"USB VID:PID={vid or '????'}:{pid or '????'}",
                    vid=vid,
                    pid=pid,
                    chip_hint=hint,
                    is_esp32_likely=likely,
                )
            )
            seen.add(dev)

    candidates.sort(key=lambda c: (not c.is_esp32_likely, c.port))
    return candidates


def _read_linux_sysfs_usb_ids(tty_name: str) -> Tuple[Optional[str], Optional[str]]:
    base = Path("/sys/class/tty") / tty_name / "device"
    if not base.exists():
        return None, None
    cur = base.resolve()
    for _ in range(4):
        vid_file = cur / "idVendor"
        pid_file = cur / "idProduct"
        if vid_file.exists() and pid_file.exists():
            try:
                return (
                    vid_file.read_text(encoding="utf-8").strip().upper(),
                    pid_file.read_text(encoding="utf-8").strip().upper(),
                )
            except OSError:
                return None, None
        cur = cur.parent
    return None, None


async def _run_cmd(cmd: List[str], env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None, timeout: float = 120.0) -> Tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=cwd,
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


class Esp32AutonomousProvisioner:
    """
    Provisioner autonomo per microcontrollori ESP32:
    1. Rileva automaticamente la porta COM/USB dell'ESP32.
    2. Risolve in sicurezza le credenziali Wi-Fi dal Password Vault dell'utente (se richiesto).
    3. Interroga il chip con esptool provando baudrate decrescenti (460800 -> 115200).
    4. Compila e flasha il firmware satellite Nuxiva via PlatformIO iniettando i parametri via env.
    """

    async def provision(self, req: Esp32ProvisionRequest) -> ProvisionJobResult:
        job_id = f"esp32_{uuid.uuid4().hex[:8]}"
        steps: List[ProvisionStepLog] = []
        detected_info: Dict[str, Any] = {}

        # Step 1: Discovery porta seriale
        t0 = time.time()
        target_port = req.port
        ports = discover_serial_ports()
        detected_info["available_ports"] = [p.model_dump() for p in ports]
        if not target_port:
            esp_ports = [p for p in ports if p.is_esp32_likely]
            if esp_ports:
                target_port = esp_ports[0].port
                detected_info["chip_hint"] = esp_ports[0].chip_hint
                steps.append(ProvisionStepLog(
                    step="serial_discovery",
                    status="ok",
                    detail=f"ESP32 rilevato automaticamente su {target_port} ({esp_ports[0].chip_hint}).",
                    duration_ms=round((time.time() - t0) * 1000, 1),
                ))
            elif req.dry_run:
                target_port = "AUTO_DRY_RUN_PORT"
                steps.append(ProvisionStepLog(
                    step="serial_discovery",
                    status="fallback",
                    detail="Nessun ESP32 collegato fisicamente; proseguo in modalità dry-run di validazione.",
                    duration_ms=round((time.time() - t0) * 1000, 1),
                ))
            else:
                steps.append(ProvisionStepLog(
                    step="serial_discovery",
                    status="failed",
                    detail="Nessuna porta USB/COM compatibile con ESP32 rilevata. Collega il cavo USB dati e riprova.",
                    duration_ms=round((time.time() - t0) * 1000, 1),
                ))
                return ProvisionJobResult(
                    job_id=job_id,
                    device_type=DeviceType.ESP32,
                    target="unassigned",
                    success=False,
                    detected_info=detected_info,
                    steps=steps,
                    summary="ESP32 non rilevato sulle porte seriali/USB.",
                )
        else:
            steps.append(ProvisionStepLog(
                step="serial_discovery",
                status="ok",
                detail=f"Uso porta seriale specificata: {target_port}.",
                duration_ms=round((time.time() - t0) * 1000, 1),
            ))

        # Step 2: Risoluzione credenziali Wi-Fi dal Password Vault (Zero-Trust in memoria)
        t1 = time.time()
        wifi_ssid = req.wifi_ssid
        wifi_password = req.wifi_password
        if req.wifi_vault_entry_id:
            try:
                revealed = password_vault_service.reveal_entry(req.user_id, req.wifi_vault_entry_id)
                wifi_ssid = wifi_ssid or revealed.username or revealed.host_or_url or revealed.label
                wifi_password = wifi_password or revealed.secret
                steps.append(ProvisionStepLog(
                    step="vault_credentials",
                    status="ok",
                    detail=f"Credenziali Wi-Fi risolte in memoria dal vault utente '{req.user_id}' (SSID: {wifi_ssid}).",
                    duration_ms=round((time.time() - t1) * 1000, 1),
                ))
            except (PermissionError, KeyError) as exc:
                steps.append(ProvisionStepLog(
                    step="vault_credentials",
                    status="failed",
                    detail=f"Impossibile accedere al vault Wi-Fi: {exc}",
                    duration_ms=round((time.time() - t1) * 1000, 1),
                ))
                return ProvisionJobResult(
                    job_id=job_id,
                    device_type=DeviceType.ESP32,
                    target=target_port,
                    success=False,
                    detected_info=detected_info,
                    steps=steps,
                    summary=f"Credenziali Wi-Fi non disponibili: {exc}",
                )
        else:
            steps.append(ProvisionStepLog(
                step="vault_credentials",
                status="ok" if wifi_ssid else "skipped",
                detail=f"SSID configurato: {wifi_ssid}" if wifi_ssid else "Nessun SSID Wi-Fi fornito (userà default firmware).",
                duration_ms=round((time.time() - t1) * 1000, 1),
            ))

        # Step 3: Verifica progetto firmware ESP32 e toolchain
        t2 = time.time()
        pio_bin = shutil.which("pio") or shutil.which("platformio")
        esptool_bin = shutil.which("esptool.py") or shutil.which("esptool")
        detected_info["firmware_dir_exists"] = ESP32_PROJECT_DIR.exists()
        detected_info["platformio_available"] = bool(pio_bin)
        detected_info["esptool_available"] = bool(esptool_bin)

        if req.dry_run:
            steps.append(ProvisionStepLog(
                step="chip_probe_and_flash",
                status="skipped",
                detail=(
                    f"Dry-run completato: firmware={'OK' if ESP32_PROJECT_DIR.exists() else 'MANCANTE'}, "
                    f"pio={'OK' if pio_bin else 'da installare'}, esptool={'OK' if esptool_bin else 'da installare'}, "
                    f"board={req.board_env}, server={req.nuxiva_server_url}."
                ),
                duration_ms=round((time.time() - t2) * 1000, 1),
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.ESP32,
                target=target_port,
                success=True,
                detected_info=detected_info,
                steps=steps,
                summary=f"Piano di auto-installazione ESP32 su {target_port} validato con successo (dry-run).",
            )

        # Step 4: Probe chip con fallback automatico baudrate
        if esptool_bin:
            probed = False
            for baud in ("460800", "115200"):
                tb = time.time()
                rc, out, err = await _run_cmd([esptool_bin, "--port", target_port, "--baud", baud, "chip_id"], timeout=20.0)
                if rc == 0:
                    detected_info["chip_probe_output"] = out.strip()[:400]
                    steps.append(ProvisionStepLog(
                        step=f"esptool_probe_{baud}",
                        status="ok" if baud == "460800" else "fallback",
                        detail=f"Chip ESP32 identificato a {baud} baud.",
                        duration_ms=round((time.time() - tb) * 1000, 1),
                    ))
                    probed = True
                    break
                steps.append(ProvisionStepLog(
                    step=f"esptool_probe_{baud}",
                    status="fallback",
                    detail=f"Probe fallito a {baud} baud ({err.strip()[:120]}), tento fallback.",
                    duration_ms=round((time.time() - tb) * 1000, 1),
                ))
            if not probed:
                return ProvisionJobResult(
                    job_id=job_id,
                    device_type=DeviceType.ESP32,
                    target=target_port,
                    success=False,
                    detected_info=detected_info,
                    steps=steps,
                    summary=f"ESP32 non risponde in bootloader su {target_port}. Tieni premuto BOOT durante il flash.",
                )

        # Step 5: Compilazione e flash PlatformIO con flag iniettati via ambiente (zero file segreti su git)
        if not pio_bin:
            steps.append(ProvisionStepLog(
                step="platformio_upload",
                status="failed",
                detail="PlatformIO ('pio') non installato su questo host. Installa con: pip install platformio",
                duration_ms=0.0,
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.ESP32,
                target=target_port,
                success=False,
                detected_info=detected_info,
                steps=steps,
                summary="Toolchain PlatformIO mancante per compilazione/flash ESP32.",
            )

        t_flash = time.time()
        build_env = os.environ.copy()
        extra_flags = [f'-DNUXIVA_SERVER_URL=\\"{req.nuxiva_server_url}\\"']
        if wifi_ssid:
            extra_flags.append(f'-DNUXIVA_WIFI_SSID=\\"{wifi_ssid}\\"')
        if wifi_password:
            extra_flags.append(f'-DNUXIVA_WIFI_PASSWORD=\\"{wifi_password}\\"')
        if req.enrollment_token:
            extra_flags.append(f'-DNUXIVA_ENROLL_TOKEN=\\"{req.enrollment_token}\\"')
        build_env["PLATFORMIO_BUILD_FLAGS"] = " ".join(extra_flags)

        rc, out, err = await _run_cmd(
            [pio_bin, "run", "-e", req.board_env, "-t", "upload", "--upload-port", target_port],
            env=build_env,
            cwd=str(ESP32_PROJECT_DIR),
            timeout=240.0,
        )
        if rc == 0:
            steps.append(ProvisionStepLog(
                step="platformio_upload",
                status="ok",
                detail=f"Firmware compilato e flashato con successo su {target_port}.",
                duration_ms=round((time.time() - t_flash) * 1000, 1),
            ))
            return ProvisionJobResult(
                job_id=job_id,
                device_type=DeviceType.ESP32,
                target=target_port,
                success=True,
                detected_info=detected_info,
                steps=steps,
                summary=f"ESP32 su {target_port} programmato e pronto a connettersi a {req.nuxiva_server_url}.",
            )

        steps.append(ProvisionStepLog(
            step="platformio_upload",
            status="failed",
            detail=(err or out).strip()[-300:],
            duration_ms=round((time.time() - t_flash) * 1000, 1),
        ))
        return ProvisionJobResult(
            job_id=job_id,
            device_type=DeviceType.ESP32,
            target=target_port,
            success=False,
            detected_info=detected_info,
            steps=steps,
            summary=f"Flash ESP32 fallito su {target_port}.",
        )


esp32_provisioner = Esp32AutonomousProvisioner()
