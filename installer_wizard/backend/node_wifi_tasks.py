from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Callable, Dict


def scan_system_wifi(run_cmd: Callable[..., Any] = subprocess.run) -> Dict[str, Any]:
    networks = []
    radio_enabled = True
    current_ssid = None
    iface_name = "Wi-Fi"

    if os.name == "nt":
        try:
            p_if = run_cmd(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
            out_if = p_if.stdout or ""
            if "Software Disabilitato" in out_if or "Disabilitato" in out_if:
                radio_enabled = False
            for line in out_if.splitlines():
                if "Nome" in line or "Name" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        iface_name = parts[1].strip()
                elif "SSID" in line and "BSSID" not in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        current_ssid = parts[1].strip()

            p_net = run_cmd(["netsh", "wlan", "show", "networks", "mode=bssid"], capture_output=True, text=True, timeout=8)
            cur = None
            for raw_line in (p_net.stdout or "").splitlines():
                line = raw_line.strip()
                if line.startswith("SSID "):
                    parts = line.split(":", 1)
                    s_name = parts[1].strip() if len(parts) > 1 else ""
                    if s_name:
                        cur = {
                            "ssid": s_name,
                            "bssid": "",
                            "signal": 75,
                            "security": "WPA2-Personal",
                            "frequency": "2.4 GHz",
                            "is_connected": s_name == current_ssid,
                        }
                        networks.append(cur)
                    else:
                        cur = None
                elif cur:
                    if "Autenticazione" in line or "Authentication" in line:
                        cur["security"] = line.split(":", 1)[1].strip()
                    elif "BSSID" in line:
                        cur["bssid"] = line.split(":", 1)[1].strip()
                    elif "Segnale" in line or "Signal" in line:
                        sig_s = line.split(":", 1)[1].strip().replace("%", "")
                        try:
                            cur["signal"] = int(sig_s)
                        except ValueError:
                            pass
                    elif "Tipo frequenza radio" in line or "Radio type" in line:
                        cur["frequency"] = line.split(":", 1)[1].strip()
        except Exception:
            pass
    else:
        try:
            p_lin = run_cmd(
                ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,SECURITY,CHAN,FREQ,IN-USE", "dev", "wifi", "list", "--rescan", "yes"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            for line in (p_lin.stdout or "").splitlines():
                parts = line.split(":")
                if len(parts) >= 6 and parts[0].strip():
                    s_name = parts[0].strip()
                    is_in_use = len(parts) > 6 and "*" in parts[6]
                    if is_in_use:
                        current_ssid = s_name
                    networks.append({
                        "ssid": s_name,
                        "bssid": parts[1].strip(),
                        "signal": int(parts[2].strip()) if parts[2].strip().isdigit() else 70,
                        "security": parts[3].strip() or "WPA2",
                        "frequency": parts[5].strip() or "5 GHz",
                        "is_connected": is_in_use,
                    })
        except Exception:
            pass

    return {
        "networks": sorted(networks, key=lambda n: n["signal"], reverse=True),
        "radio_enabled": radio_enabled,
        "current_ssid": current_ssid,
        "interface": iface_name,
    }


def connect_wifi(ssid: str, password: str, interface: str | None, run_cmd: Callable[..., Any] = subprocess.run) -> Dict[str, Any]:
    success = False
    error_msg = ""
    if os.name == "nt":
        try:
            profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption>
            <authentication>{'WPA2PSK' if password else 'open'}</authentication>
            <encryption>{'AES' if password else 'none'}</encryption>
            <useOneX>false</useOneX>
        </authEncryption>
        {f'<sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey>' if password else ''}
    </security></MSM>
</WLANProfile>"""
            tmp_xml_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"nuxiva_wifi_{int(time.time())}.xml")
            with open(tmp_xml_path, "w", encoding="utf-8") as f:
                f.write(profile_xml)
            run_cmd(["netsh", "wlan", "add", "profile", f"filename={tmp_xml_path}"], capture_output=True, timeout=5)
            try:
                os.remove(tmp_xml_path)
            except OSError:
                pass
            p_conn = run_cmd(["netsh", "wlan", "connect", f"name={ssid}"], capture_output=True, text=True, timeout=8)
            success = p_conn.returncode == 0
            if not success:
                error_msg = p_conn.stdout or p_conn.stderr or "Connection failed"
        except Exception as exc:
            error_msg = str(exc)
    else:
        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", password])
            if interface:
                cmd.extend(["ifname", interface])
            p_conn = run_cmd(cmd, capture_output=True, text=True, timeout=12)
            success = p_conn.returncode == 0
            if not success:
                error_msg = p_conn.stdout or p_conn.stderr or "Connection failed"
        except Exception as exc:
            error_msg = str(exc)
    return {"success": success, "ssid": ssid, "error": error_msg}


def collect_node_tasks(capabilities: Dict[str, bool], run_cmd: Callable[..., Any] = subprocess.run) -> Dict[str, Any]:
    import psutil

    cpu_pct = psutil.cpu_percent(interval=0.08)
    cpu_cores = psutil.cpu_count(logical=True) or 1
    cpu_f = psutil.cpu_freq()
    cpu_freq_mhz = round(cpu_f.current, 0) if cpu_f else 0.0
    vm = psutil.virtual_memory()
    ram_data = {
        "used_gb": round(vm.used / (1024**3), 2),
        "total_gb": round(vm.total / (1024**3), 2),
        "percent": vm.percent,
    }
    gpu_data = None
    gpu_proc_map: Dict[int, float] = {}
    try:
        p_gpu = run_cmd(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if p_gpu.returncode == 0 and p_gpu.stdout.strip():
            g_parts = [p.strip() for p in p_gpu.stdout.strip().splitlines()[0].split(",")]
            if len(g_parts) >= 5:
                gpu_data = {
                    "name": g_parts[0],
                    "memory_total_mb": float(g_parts[1]),
                    "memory_used_mb": float(g_parts[2]),
                    "utilization_percent": float(g_parts[3]),
                    "temperature_c": float(g_parts[4]),
                }
        p_apps = run_cmd(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if p_apps.returncode == 0 and p_apps.stdout.strip():
            for line in p_apps.stdout.strip().splitlines():
                parts = [x.strip() for x in line.split(",")]
                if len(parts) >= 2 and parts[0].isdigit():
                    mem_val = float(parts[1]) if parts[1].replace(".", "").isdigit() else 0.0
                    gpu_proc_map[int(parts[0])] = mem_val
    except Exception:
        pass

    processes = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username"]):
        try:
            info = p.info
            p_name = info.get("name") or "unknown"
            mem_mb = round(info["memory_info"].rss / (1024 * 1024), 1) if info.get("memory_info") else 0.0
            pid = info["pid"]
            lname = p_name.lower()
            category = "system"
            if any(k in lname for k in ("ollama", "python", "torch", "llama", "vllm", "cuda")):
                category = "ai_engine"
            elif any(k in lname for k in ("nuxiva", "supervisor", "spatial", "node", "vite", "cargo")):
                category = "nuxiva"
            processes.append({
                "pid": pid,
                "name": p_name,
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                "ram_mb": mem_mb,
                "gpu_memory_mb": gpu_proc_map.get(pid, 0.0),
                "status": info.get("status") or "running",
                "user": info.get("username") or "",
                "category": category,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    processes.sort(key=lambda x: (x["category"] == "ai_engine", x["ram_mb"]), reverse=True)
    return {
        "cpu": {"percent": cpu_pct, "cores": cpu_cores, "freq_mhz": cpu_freq_mhz},
        "ram": ram_data,
        "gpu": gpu_data,
        "processes": processes[:80],
        "capabilities": capabilities,
    }
