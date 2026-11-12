from __future__ import annotations

import asyncio
import os
import socket
import subprocess
from typing import Any, Dict, Optional, Tuple

import node_wifi_tasks
import psutil


def get_cable_status() -> Dict[str, Any]:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    for iface, stat in stats.items():
        if not stat.isup:
            continue
        lname = iface.lower()
        if any(w in lname for w in ("loopback", "pseudo", "bluetooth", "vethernet", "wsl", "docker", "br-", "tap", "tun", "veth")):
            continue
        if any(w in lname for w in ("wi-fi", "wifi", "wlan", "wireless", "802.11")):
            continue
        addr_list = addrs.get(iface, [])
        ipv4 = next(
            (
                a.address
                for a in addr_list
                if a.family == socket.AF_INET
                and not a.address.startswith("127.")
                and not a.address.startswith("169.254.")
            ),
            None,
        )
        if ipv4:
            return {
                "connected": True,
                "interface": iface,
                "ip": ipv4,
                "speed_mbps": stat.speed if stat.speed > 0 else 1000,
            }
    return {
        "connected": False,
        "interface": "",
        "ip": "",
        "speed_mbps": 0,
    }


def has_wifi_adapter() -> Tuple[bool, str]:
    stats = psutil.net_if_stats()
    for iface in stats.keys():
        lname = iface.lower()
        if any(w in lname for w in ("wi-fi", "wifi", "wlan", "wireless", "802.11")):
            return True, iface
    if os.name == "nt":
        try:
            p = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
            if "GUID" in p.stdout or "Nome" in p.stdout or "Name" in p.stdout:
                return True, "Wi-Fi"
        except Exception:
            pass
    else:
        try:
            p = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE", "dev"], capture_output=True, text=True, timeout=4)
            for line in p.stdout.splitlines():
                if ":wifi" in line:
                    return True, line.split(":")[0]
        except Exception:
            pass
    return False, ""


def _scan_wifi_sync() -> Dict[str, Any]:
    has_adapter, iface = has_wifi_adapter()
    if not has_adapter:
        return {
            "networks": [],
            "radio_enabled": False,
            "current_ssid": None,
            "interface": "",
            "has_adapter": False,
        }
    data = node_wifi_tasks.scan_system_wifi()
    data["has_adapter"] = True
    if not data.get("interface"):
        data["interface"] = iface
    return data


async def get_wifi_status() -> Dict[str, Any]:
    cable = await asyncio.to_thread(get_cable_status)
    wifi_data = await asyncio.to_thread(_scan_wifi_sync)
    has_wifi = bool(wifi_data.get("has_adapter"))
    current_ssid = wifi_data.get("current_ssid")
    is_wifi_connected = bool(current_ssid)
    is_cable_connected = bool(cable.get("connected"))

    return {
        "has_wifi": has_wifi,
        "is_cable_connected": is_cable_connected,
        "cable": cable,
        "is_optional": is_cable_connected,
        "wifi_connected": is_wifi_connected,
        "current_ssid": current_ssid,
        "interface": wifi_data.get("interface") or "",
        "radio_enabled": wifi_data.get("radio_enabled", True),
        "networks": wifi_data.get("networks", []),
        "can_proceed": is_cable_connected or is_wifi_connected,
    }


async def scan_wifi() -> Dict[str, Any]:
    wifi_data = await asyncio.to_thread(_scan_wifi_sync)
    return {
        "success": True,
        "has_wifi": bool(wifi_data.get("has_adapter")),
        "networks": wifi_data.get("networks", []),
        "current_ssid": wifi_data.get("current_ssid"),
        "interface": wifi_data.get("interface") or "",
    }


async def connect_wifi(ssid: str, password: str, interface: Optional[str] = None) -> Dict[str, Any]:
    clean_ssid = str(ssid or "").strip()
    if not clean_ssid:
        return {"success": False, "error": "SSID non valido"}
    res = await asyncio.to_thread(node_wifi_tasks.connect_wifi, clean_ssid, password, interface)
    return res
