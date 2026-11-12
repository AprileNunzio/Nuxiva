from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
import urllib.request
from typing import Any

import psutil

log = logging.getLogger("nuxiva.setup.network")


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _get_interfaces() -> list[dict[str, Any]]:
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    result = []
    for iface, addr_list in addrs.items():
        stat = stats.get(iface)
        ipv4 = next((a.address for a in addr_list if a.family == socket.AF_INET), None)
        if not ipv4 or ipv4.startswith("127."):
            continue
        ipv6 = next((a.address for a in addr_list if a.family == socket.AF_INET6 and not a.address.startswith("fe80")), "")
        mac = next((a.address for a in addr_list if a.family == psutil.AF_LINK), "")
        netmask = next((a.netmask for a in addr_list if a.family == socket.AF_INET), "")
        speed = stat.speed if stat and stat.speed > 0 else 1000
        mtu = stat.mtu if stat else 1500
        is_up = stat.isup if stat else True
        result.append({
            "name": iface,
            "ip": ipv4,
            "ipv6": ipv6,
            "mac": mac,
            "netmask": netmask,
            "speed_mbps": speed,
            "mtu": mtu,
            "is_up": is_up,
        })
    return result


def _get_public_ip_and_ping() -> tuple[str, float]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "Nuxiva/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rtt = round((time.perf_counter() - t0) * 1000, 1)
            return str(data.get("ip", "Offline")), rtt
    except Exception:
        return "Offline", 0.0


def _get_dns_servers() -> list[str]:
    servers: list[str] = []
    try:
        from pathlib import Path
        resolv = Path("/etc/resolv.conf")
        if resolv.exists():
            for line in resolv.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("nameserver"):
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] not in servers:
                        servers.append(parts[1])
    except Exception:
        pass
    if not servers:
        servers = ["1.1.1.1", "8.8.8.8"]
    return servers


def _format_bytes(num: int) -> str:
    val = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(val) < 1024.0:
            return f"{val:3.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"


async def get_network_diagnostics() -> dict[str, Any]:
    local_ip = await asyncio.to_thread(_get_local_ip)
    public_ip, ping_ms = await asyncio.to_thread(_get_public_ip_and_ping)
    interfaces = await asyncio.to_thread(_get_interfaces)
    dns = await asyncio.to_thread(_get_dns_servers)
    io = psutil.net_io_counters()

    return {
        "hostname": socket.gethostname(),
        "local_ip": local_ip,
        "public_ip": public_ip,
        "ping_ms": ping_ms,
        "dns": dns,
        "interfaces": interfaces,
        "traffic": {
            "bytes_sent": io.bytes_sent,
            "bytes_recv": io.bytes_recv,
            "bytes_sent_fmt": _format_bytes(io.bytes_sent),
            "bytes_recv_fmt": _format_bytes(io.bytes_recv),
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "drop_in": io.dropin,
            "drop_out": io.dropout,
            "err_in": io.errin,
            "err_out": io.errout,
        },
        "timestamp": int(time.time()),
    }
